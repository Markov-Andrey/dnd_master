from collections import defaultdict
from typing import Callable, Any


class EventBus:
    """Simple synchronous publish/subscribe event bus."""

    def __init__(self):
        self._listeners: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event: str, callback: Callable):
        self._listeners[event].append(callback)

    def unsubscribe(self, event: str, callback: Callable):
        self._listeners[event] = [cb for cb in self._listeners[event] if cb != callback]

    def emit(self, event: str, data: Any = None):
        for callback in list(self._listeners[event]):
            callback(data)


bus = EventBus()
