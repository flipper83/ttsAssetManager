from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class EventKind(str, Enum):
    INFO = "info"
    WARNING = "warning"
    UPLOAD = "upload"
    SKIP = "skip"
    DELETE = "delete"
    COMPOSE = "compose"


@dataclass
class ProgressEvent:
    kind: EventKind
    message: str
    data: dict[str, Any] = field(default_factory=dict)


ProgressCallback = Callable[[ProgressEvent], None]


def noop(_event: ProgressEvent) -> None:
    pass
