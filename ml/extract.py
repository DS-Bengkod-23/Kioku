import os
import json
from pathlib import Path
from openai import OpenAI, BadRequestError, AuthenticationError, PermissionDeniedError, NotFoundError
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


def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def _complete_openai(prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY tidak ditemukan di environment")

    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    try:
        client = OpenAI(api_key=api_key)
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
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=genai_types.GenerateContentConfig(response_mime_type="application/json"),
        )
        return response.text.strip()
    except genai_errors.ClientError as e:
        raise PermanentMLError(f"Gemini tidak bisa diakses (permanen): {e}") from e
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

    return SummaryResult(**data)


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

    items = data.get("action_items", []) if isinstance(data, dict) else data

    return [ActionItem(**item) for item in items]
