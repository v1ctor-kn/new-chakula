# recipes.py
import os
import requests
import json
from typing import Any

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

SYSTEM_PROMPT = (
    "You are a helpful recipe generator. Given a short list of ingredients and optional dietary notes, "
    "return a JSON object with a top-level 'recipes' array. Each recipe must have: "
    "title (string), description (string), ingredients (array of strings), steps (array of strings), "
    "prep_minutes (integer), cook_minutes (integer). Return only valid JSON and nothing else."
)

HEADERS = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "Content-Type": "application/json",
}

def generate_recipes(ingredients: str, notes: str = "", limit: int = 3) -> Any:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set in environment")

    user_prompt = f"Ingredients: {ingredients}\nNotes: {notes}\nReturn {limit} recipes."

    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 800,
    }

    resp = requests.post(OPENAI_URL, headers=HEADERS, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    text = data["choices"][0]["message"]["content"].strip()

    # Try parsing JSON that the model returned. If it gave extra text, try to find a JSON block.
    try:
        parsed = json.loads(text)
        return parsed
    except Exception:
        # attempt to extract JSON substring
        import re
        m = re.search(r"(\{.*\}|\[.*\])", text, flags=re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception as e:
                raise RuntimeError(f"Failed to parse JSON from model output: {e}\nRaw output:\n{text}")
        else:
            raise RuntimeError("Model did not return JSON. Raw output:\n" + text)
