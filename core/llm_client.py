"""LLM-клиент: чат, JSON-ответы, очистка thinking-тегов."""
import json, re, requests
from core.config import LLM_BASE_URL, LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS

_THINK_RE = [re.compile(p, re.DOTALL | re.IGNORECASE) for p in [
    r"<think>.*?</think>", r"<reasoning>.*?</reasoning>",
    r".*?✅\s*Text:\s*", r"^.*?Final output:\s*",
    r"^.*?Ready\. Output:\s*", r"^.*?✅\s*",
]]


def _strip(text):
    for pat in _THINK_RE: text = pat.sub("", text, count=1)
    return text.strip()


def chat(system_prompt, messages):
    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "system", "content": system_prompt}] + messages,
        "temperature": LLM_TEMPERATURE, "max_tokens": LLM_MAX_TOKENS,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    resp = requests.post(f"{LLM_BASE_URL}/chat/completions", json=payload, timeout=120)
    resp.raise_for_status()
    msg = resp.json()["choices"][0]["message"]
    return _strip(msg.get("content") or msg.get("reasoning_content") or "")


def chat_json(system_prompt, messages):
    raw = chat(system_prompt, messages).strip()
    if raw.startswith("```"): raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(raw)
