from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SessionState(str, Enum):
    IDLE = "IDLE"
    MOVING = "MOVING"
    WAITING_FOR_LEFT = "WAITING_FOR_LEFT"
    WAITING_FOR_RIGHT = "WAITING_FOR_RIGHT"
    DETECTED = "DETECTED"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


class RobotCommand(str, Enum):
    MOVE = "MOVE"
    PUNCH_REQUEST_LEFT = "PUNCH_REQUEST_LEFT"
    PUNCH_REQUEST_RIGHT = "PUNCH_REQUEST_RIGHT"


class PunchSide(str, Enum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    NONE = "NONE"


class EventStatus(str, Enum):
    PENDING = "PENDING"
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    TIMEOUT = "TIMEOUT"


@dataclass
class CommandResult:
    status: str
    state: SessionState
    message: str
    event_id: Optional[str] = None
    movement_target: Optional[dict] = None
