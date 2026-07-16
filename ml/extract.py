import os
import json
from pathlib import Path
from openai import OpenAI, BadRequestError, AuthenticationError, PermissionDeniedError, NotFoundError
from pydantic import ValidationError
from google import genai
from google.genai import types as genai_types
from google.genai import errors as genai_errors
try:
    from .schemas import SummaryResult, ActionItem
except ImportError:
    from schemas import SummaryResult, ActionItem
try:
    from .errors import PermanentMLError
except ImportError:
    from errors import PermanentMLError

PROMPTS_DIR = Path(__file__).parent / "prompts"

# Timeout HTTP untuk panggilan OpenAI/Gemini — request di sini teks saja (tanpa
# audio), jadi lebih ketat dari ml/transcribe.py. Tanpa ini, koneksi yang hang
# bisa memblokir worker Celery tanpa batas waktu.
_LLM_TIMEOUT_SECONDS = 120


def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def _complete_openai(prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY tidak ditemukan di environment")

    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    try:
        client = OpenAI(api_key=api_key, timeout=_LLM_TIMEOUT_SECONDS)
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content.strip()
    except (BadRequestError, AuthenticationError, PermissionDeniedError, NotFoundError) as e:
        raise PermanentMLError(f"OpenAI tidak bisa diakses (permanen): {e}") from e
    except Exception as e:
        raise RuntimeError(f"OpenAI tidak bisa diakses: {e}") from e


def _complete_gemini(prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY tidak ditemukan di environment")

    model_name = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

    try:
        client = genai.Client(
            api_key=api_key,
            http_options=genai_types.HttpOptions(timeout=_LLM_TIMEOUT_SECONDS * 1000),
        )
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=genai_types.GenerateContentConfig(response_mime_type="application/json"),
        )
        text = response.text
        if not text:
            # response.text bisa None walau HTTP 200 (safety filter/candidate tanpa
            # teks) — sama seperti di ml/transcribe.py. Tanpa guard ini, .strip()
            # lempar AttributeError polos yang ketutup jadi RuntimeError generik
            # "tidak bisa diakses", padahal ini kegagalan permanen (blokir konten),
            # bukan masalah konektivitas.
            if not response.candidates:
                block_reason = getattr(response.prompt_feedback, "block_reason", None)
                raise PermanentMLError(f"Gemini tidak mengembalikan hasil (prompt diblokir: {block_reason})")
            candidate = response.candidates[0]
            raise PermanentMLError(
                f"Gemini tidak mengembalikan teks "
                f"(finish_reason={candidate.finish_reason}, finish_message={candidate.finish_message})"
            )
        return text.strip()
    except genai_errors.ClientError as e:
        raise PermanentMLError(f"Gemini tidak bisa diakses (permanen): {e}") from e
    except PermanentMLError:
        raise
    except Exception as e:
        raise RuntimeError(f"Gemini tidak bisa diakses: {e}") from e


def _complete(prompt: str) -> str:
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    if provider == "gemini":
        return _complete_gemini(prompt)
    return _complete_openai(prompt)


def extract_summary(transcript_text: str) -> SummaryResult:
    template = _load_prompt("summary.txt")
    prompt = template.format(transcript=transcript_text)

    raw = _complete(prompt)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Output LLM bukan JSON valid: {e}") from e

    try:
        return SummaryResult(**data)
    except (TypeError, ValidationError) as e:
        # JSON valid secara syntax tapi field-nya tidak cocok skema SummaryResult
        # (mis. "decisions" berupa string, bukan list) — tanpa guard ini,
        # ValidationError/TypeError mentah bocor sebagai exception tak terklasifikasi
        # yang ikut ke jalur retry default, padahal ini kegagalan yang akan identik lagi.
        raise ValueError(f"Output LLM tidak sesuai skema SummaryResult: {e}\nRaw: {raw[:500]}") from e


def extract_action_items(
    transcript_text: str,
    participant_names: list[str],
) -> list[ActionItem]:
    template = _load_prompt("action_items.txt")
    names_str = ", ".join(participant_names) if participant_names else "tidak diketahui"
    prompt = template.format(transcript=transcript_text, participant_names=names_str)

    raw = _complete(prompt)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Output LLM bukan JSON valid: {e}") from e

    if isinstance(data, dict):
        # Dulu default diam-diam ke [] kalau key "action_items" tidak ada (mis. LLM
        # drift ke key lain seperti "items"/"actionItems") — action item yang
        # sebetulnya ada di transkrip jadi hilang tanpa jejak sama sekali di log.
        if "action_items" not in data:
            raise ValueError(
                f"Output LLM tidak punya key 'action_items': {raw[:500]}"
            )
        items = data["action_items"]
    else:
        items = data

    try:
        return [ActionItem(**item) for item in items]
    except (TypeError, ValidationError) as e:
        raise ValueError(f"Output LLM tidak sesuai skema ActionItem: {e}\nRaw: {raw[:500]}") from e
