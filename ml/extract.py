import os
import json
from pathlib import Path
from google import genai
from google.genai import types as genai_types
try:
    from .schemas import SummaryResult, ActionItem
except ImportError:
    from schemas import SummaryResult, ActionItem

PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def _complete(prompt: str) -> str:
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
    except Exception as e:
        raise RuntimeError(f"Gemini tidak bisa diakses: {e}") from e


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
        items = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Output LLM bukan JSON valid: {e}") from e

    return [ActionItem(**item) for item in items]
