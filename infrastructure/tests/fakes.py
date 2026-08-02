"""Minimal Redis stand-in for deterministic queue / idempotency unit tests."""

from __future__ import annotations

from collections import defaultdict, deque


class FakeRedis:
    """Implements the RedisClient / RedisHashClient subsets used by adapters."""

    def __init__(self) -> None:
        self._lists: dict[str, deque[str]] = defaultdict(deque)
        self._hashes: dict[str, dict[str, str]] = defaultdict(dict)

    def rpush(self, name: str, *values: str) -> int:
        for value in values:
            self._lists[name].append(value)
        return len(self._lists[name])

    def lmove(
        self,
        first_list: str,
        second_list: str,
        src: str = "LEFT",
        dest: str = "RIGHT",
    ) -> str | None:
        source = self._lists[first_list]
        if not source:
            return None
        value = source.popleft() if src == "LEFT" else source.pop()
        target = self._lists[second_list]
        if dest == "RIGHT":
            target.append(value)
        else:
            target.appendleft(value)
        return value

    def blmove(
        self,
        first_list: str,
        second_list: str,
        timeout: float,
        src: str = "LEFT",
        dest: str = "RIGHT",
    ) -> str | None:
        del timeout
        return self.lmove(first_list, second_list, src=src, dest=dest)

    def lrem(self, name: str, count: int, value: str) -> int:
        source = self._lists[name]
        removed = 0
        if count == 0:
            new = deque(item for item in source if item != value)
            removed = len(source) - len(new)
            self._lists[name] = new
            return removed
        remaining = deque(source)
        source.clear()
        for item in remaining:
            if item == value and removed < abs(count):
                removed += 1
                continue
            source.append(item)
        return removed

    def lrange(self, name: str, start: int, end: int) -> list[str]:
        items = list(self._lists[name])
        if end == -1:
            return items[start:]
        return items[start : end + 1]

    def hget(self, name: str, key: str) -> str | None:
        return self._hashes[name].get(key)

    def hset(self, name: str, key: str, value: str) -> int:
        created = 0 if key in self._hashes[name] else 1
        self._hashes[name][key] = value
        return created
