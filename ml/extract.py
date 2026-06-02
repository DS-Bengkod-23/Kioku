import os
import json
from pathlib import Path
from openai import OpenAI
try:
    from .schemas import SummaryResult, ActionItem
except ImportError:
    from schemas import SummaryResult, ActionItem

PROMPTS_DIR = Path(__file__).parent / "prompts"
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def extract_summary(transcript_text: str) -> SummaryResult:
    template = _load_prompt("summary.txt")
    prompt = template.format(transcript=transcript_text)

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw)
    except Exception as e:
        raise RuntimeError(f"OpenAI tidak bisa diakses: {e}") from e
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

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content.strip()
        items = json.loads(raw)
    except Exception as e:
        raise RuntimeError(f"OpenAI tidak bisa diakses: {e}") from e
    except json.JSONDecodeError as e:
        raise ValueError(f"Output LLM bukan JSON valid: {e}") from e

    return [ActionItem(**item) for item in items]
