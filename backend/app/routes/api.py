from __future__ import annotations

import time

from flask import Blueprint, Response, jsonify, request

from app.core.session_manager import SessionManager, parse_frame_payload
from app.core.state_machine import RobotCommand
from app.storage.db import DEFAULT_USER_ID, get_user

COMMAND_ALIASES = {
    "PUNCH_REQUST_LEFT": RobotCommand.PUNCH_REQUEST_LEFT.value,
    "PUNSH_REQUEST_RIGHT": RobotCommand.PUNCH_REQUEST_RIGHT.value,
}


def create_api_blueprint(session_manager: SessionManager) -> Blueprint:
    api = Blueprint("api", __name__)

    @api.get("/health")
    def health() -> Response:
        return jsonify({"status": "ok"})

    @api.post("/sessions")
    def create_session() -> Response:
        session = session_manager.create_session()
        user = get_user(DEFAULT_USER_ID)
        return jsonify(
            {
                "status": "OK",
                "session_id": session.session_id,
                "user_id": user["user_id"] if user else DEFAULT_USER_ID,
                "state": session.state.value,
                "username": user["username"] if user else None,
            }
        ), 201

    @api.post("/sessions/<session_id>/command")
    def command(session_id: str) -> Response:
        payload = request.get_json(force=True, silent=False) or {}
        command_value = COMMAND_ALIASES.get(payload.get("command"), payload.get("command"))
        if command_value not in {command.value for command in RobotCommand}:
            return jsonify({"status": "ERROR", "message": "Unsupported command"}), 400
        try:
            result = session_manager.handle_command(session_id, command_value)
        except KeyError:
            return jsonify({"status": "ERROR", "message": "Unknown session"}), 404
        return jsonify(
            {
                "status": result.status,
                "state": result.state.value,
                "message": result.message,
                "event_id": result.event_id,
                "movement_target": result.movement_target,
            }
        )

    @api.post("/sessions/<session_id>/frames")
    def frames(session_id: str) -> Response:
        try:
            frame_bytes = parse_frame_payload(request)
            result = session_manager.process_uploaded_frame(session_id, frame_bytes)
        except KeyError:
            return jsonify({"status": "ERROR", "message": "Unknown session"}), 404
        except ValueError as exc:
            return jsonify({"status": "ERROR", "message": str(exc)}), 400
        return jsonify(result)

    @api.get("/sessions/<session_id>/status")
    def status(session_id: str) -> Response:
        try:
            payload = session_manager.build_status_payload(session_id)
        except KeyError:
            return jsonify({"status": "ERROR", "message": "Unknown session"}), 404
        user_record = get_user(DEFAULT_USER_ID)
        payload["user_id"] = user_record["user_id"] if user_record else DEFAULT_USER_ID
        payload["username"] = user_record["username"] if user_record else None
        return jsonify({"status": "OK", **payload})

    @api.get("/users/<user_id>")
    def user(user_id: str) -> Response:
        user_record = get_user(user_id)
        if not user_record:
            return jsonify({"status": "ERROR", "message": "Unknown user"}), 404
        return jsonify(
            {
                "status": "OK",
                "user_id": user_record["user_id"],
                "username": user_record["username"],
            }
        )

    @api.get("/sessions/<session_id>/stream")
    def stream(session_id: str) -> Response:
        def generate():
            while True:
                try:
                    frame_bytes = session_manager.latest_frame(session_id)
                except KeyError:
                    break
                if frame_bytes:
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                    )
                time.sleep(0.15)

        return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

    return api
