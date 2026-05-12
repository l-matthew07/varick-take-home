from datetime import datetime, timezone
from typing import Any


def enum_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
