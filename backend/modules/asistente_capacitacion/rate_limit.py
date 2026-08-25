"""Límite local defensivo; Railway puede complementarlo con límite distribuido."""
from collections import defaultdict, deque
from threading import Lock
from time import monotonic

_events=defaultdict(deque);_lock=Lock()
def allow(key: str, limit: int, window_seconds: int=60) -> bool:
    now=monotonic()
    with _lock:
        queue=_events[key]
        while queue and now-queue[0]>=window_seconds: queue.popleft()
        if len(queue)>=limit: return False
        queue.append(now);return True
