"""
간단한 알림 중복 방지(De-dup) 유틸.

메모리 기반으로 일정 시간(TTL) 내 동일 키의 알림을 1회만 허용한다.
프로세스 단위 동작이므로 여러 워커/인스턴스 환경에서는
외부 캐시/DB 등을 사용하는 것을 권장.
"""

from __future__ import annotations

import os
import time
from threading import RLock
from typing import Dict

_lock = RLock()
_cache: Dict[str, float] = {}
_DEFAULT_TTL = int(os.getenv("ALERT_DEDUP_TTL", "600"))  # 기본 10분


def _now() -> float:
    return time.time()


def _cleanup(ttl: int) -> None:
    """TTL 만료된 항목을 정리한다."""
    now = _now()
    expired = [k for k, ts in _cache.items() if now - ts > ttl]
    for k in expired:
        _cache.pop(k, None)


def should_send(key: str, *, ttl: int | None = None) -> bool:
    """
    주어진 key에 대해 TTL 내에 이미 전송된 알림이 있는지 확인.
    True면 전송 가능, False면 스킵.
    """
    ttl = _DEFAULT_TTL if ttl is None else ttl
    with _lock:
        _cleanup(ttl)
        ts = _cache.get(key)
        if ts is None:
            return True
        return (_now() - ts) > ttl


def mark_sent(key: str) -> None:
    """해당 key로 전송되었음을 기록."""
    with _lock:
        _cache[key] = _now()
