from __future__ import annotations

import base64
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import cv2
import numpy as np

from app.core.reaction_service import random_movement_target
from app.core.state_machine import CommandResult, EventStatus, PunchSide, RobotCommand, SessionState
from app.detection.detector_service import SessionDetector
from app.storage.db import DEFAULT_USER_ID, DEFAULT_USERNAME, finalize_event, insert_event, upsert_session, upsert_user


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SessionRuntime:
    session_id: str
    started_at: str
    updated_at: str
    state: SessionState = SessionState.IDLE
    current_command: Optional[RobotCommand] = None
    current_event_id: Optional[str] = None
    command_displayed_at: Optional[str] = None
    moving_until: Optional[float] = None
    latest_frame_jpeg: bytes = b""
    detector: SessionDetector = field(default_factory=SessionDetector)


class SessionManager:
    def __init__(self) -> None:
        self.sessions: dict[str, SessionRuntime] = {}
        self.lock = threading.Lock()

    def create_session(self) -> SessionRuntime:
        with self.lock:
            session_id = str(uuid.uuid4())
            now = utc_now()
            session = SessionRuntime(session_id=session_id, started_at=now, updated_at=now)
            self.sessions[session_id] = session
            upsert_user(DEFAULT_USER_ID, DEFAULT_USERNAME)
            self._persist(session)
            return session

    def get_session(self, session_id: str) -> Optional[SessionRuntime]:
        with self.lock:
            session = self.sessions.get(session_id)
            if not session:
                return None
            self._refresh_moving_state(session)
            return session

    def handle_command(self, session_id: str, command_value: str) -> CommandResult:
        with self.lock:
            session = self.sessions.get(session_id)
            if not session:
                raise KeyError(session_id)
            self._refresh_moving_state(session)
            if session.state == SessionState.MOVING:
                return CommandResult(status="MOVING", state=session.state, message="MOVING currently")

            command = RobotCommand(command_value)
            now = utc_now()
            session.updated_at = now

            if command == RobotCommand.MOVE:
                session.state = SessionState.MOVING
                session.current_command = command
                session.current_event_id = None
                session.command_displayed_at = now
                session.moving_until = time.time() + 3.0
                movement_target = random_movement_target()
                self._persist(session)
                return CommandResult(status="OK", state=session.state, message="Movement plan created", movement_target=movement_target)

            expected_side = PunchSide.LEFT if command == RobotCommand.PUNCH_REQUEST_LEFT else PunchSide.RIGHT
            session.state = SessionState.WAITING_FOR_LEFT if expected_side == PunchSide.LEFT else SessionState.WAITING_FOR_RIGHT
            session.current_command = command
            session.command_displayed_at = now
            session.current_event_id = str(uuid.uuid4())
            insert_event(session.current_event_id, session.session_id, now, expected_side.value, EventStatus.PENDING.value)
            self._persist(session)
            return CommandResult(
                status="OK",
                state=session.state,
                message=f"Waiting for {expected_side.value} punch",
                event_id=session.current_event_id,
            )

    def process_uploaded_frame(self, session_id: str, frame_bytes: bytes) -> dict:
        with self.lock:
            session = self.sessions.get(session_id)
            if not session:
                raise KeyError(session_id)
            self._refresh_moving_state(session)
            frame = self._decode_frame(frame_bytes)
            detection, debug_jpeg = session.detector.process_frame(frame)
            session.latest_frame_jpeg = debug_jpeg
            session.updated_at = utc_now()

            if session.state not in (SessionState.WAITING_FOR_LEFT, SessionState.WAITING_FOR_RIGHT):
                self._persist(session)
                return {"status": "OK", "state": session.state.value}

            expected_action = PunchSide.LEFT if session.state == SessionState.WAITING_FOR_LEFT else PunchSide.RIGHT
            if detection and detection.action != PunchSide.NONE:
                status = EventStatus.MATCH if detection.action == expected_action else EventStatus.MISMATCH
                finalize_event(
                    session.current_event_id,
                    detection.action.value,
                    utc_now(),
                    status.value,
                    detection.confidence,
                )
                session.state = SessionState.DETECTED
                self._persist(session)
                return {
                    "status": "OK",
                    "state": session.state.value,
                    "command": expected_action.value,
                    "action": detection.action.value,
                    "punch_type": detection.punch_type,
                    "confidence": detection.confidence,
                    "result": status.value,
                }

            command_age = time.time() - datetime.fromisoformat(session.command_displayed_at).timestamp()
            if command_age > 5.0 and session.current_event_id:
                finalize_event(session.current_event_id, PunchSide.NONE.value, utc_now(), EventStatus.TIMEOUT.value, None)
                session.state = SessionState.TIMEOUT
                self._persist(session)
                return {"status": "OK", "state": session.state.value, "result": EventStatus.TIMEOUT.value}

            self._persist(session)
            return {"status": "OK", "state": session.state.value}

    def build_status_payload(self, session_id: str) -> dict:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(session_id)
        return {
            "session_id": session.session_id,
            "state": session.state.value,
            "current_command": session.current_command.value if session.current_command else None,
            "event_id": session.current_event_id,
            "updated_at": session.updated_at,
        }

    def latest_frame(self, session_id: str) -> Optional[bytes]:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(session_id)
        return session.latest_frame_jpeg or None

    @staticmethod
    def _decode_frame(frame_bytes: bytes) -> np.ndarray:
        array = np.frombuffer(frame_bytes, dtype=np.uint8)
        frame = cv2.imdecode(array, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("Unable to decode uploaded frame")
        return frame

    def _refresh_moving_state(self, session: SessionRuntime) -> None:
        if session.state == SessionState.MOVING and session.moving_until and time.time() >= session.moving_until:
            session.state = SessionState.IDLE
            session.current_command = None
            session.command_displayed_at = None
            session.moving_until = None
            session.updated_at = utc_now()
            self._persist(session)

    def _persist(self, session: SessionRuntime) -> None:
        upsert_session(
            session.session_id,
            session.started_at,
            session.updated_at,
            session.state.value,
            session.current_command.value if session.current_command else None,
            session.current_event_id,
        )


def parse_frame_payload(request) -> bytes:
    if "frame" in request.files:
        return request.files["frame"].read()
    payload = request.get_json(silent=True) or {}
    frame_b64 = payload.get("frame_base64")
    if not frame_b64:
        raise ValueError("Expected multipart file 'frame' or JSON field 'frame_base64'")
    if "," in frame_b64:
        frame_b64 = frame_b64.split(",", 1)[1]
    return base64.b64decode(frame_b64)
