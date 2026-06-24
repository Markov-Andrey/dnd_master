"""Суммаризация: блочная (каждые 20 сообщений) и финальная."""
from core import llm_client

_BLOCK_PROMPT = """Суммаризируй блок RPG-диалога. Строго JSON:
{"summary":"1-2 предложения","facts":["факт1","факт2"],"emotional_tone":"тон","relationship_moments":["момент"]}"""


_FINAL_PROMPT = """Объедини все саммари в итог встречи. Строго JSON:
{"summary":"3-5 предложений","facts":["1","2","3"],"emotional_tone":"тон","relationship_moments":["момент"]}"""


def _format_history(history):
    return "\n".join(f"{m['role'].upper()}: {m['content'][:200]}" for m in history[-10:])


def summarize_block(dialogue_history, current_summary=""):
    prompt = f"Предыдущая саммари:\n{current_summary}\n\nДиалог:\n{_format_history(dialogue_history)}" if current_summary else _format_history(dialogue_history)
    return llm_client.chat_json(_BLOCK_PROMPT, [{"role": "user", "content": prompt}])


def summarize_final(dialogue_history, summaries):
    prev = "\n---\n".join(summaries[-3:]) if summaries else "нет блоков"
    prompt = f"Предыдущие блоки:\n{prev}\n\nДиалог:\n{_format_history(dialogue_history)}"
    return llm_client.chat_json(_FINAL_PROMPT, [{"role": "user", "content": prompt}])
