from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.session_manager import SessionManager


WINDOW_NAME = "Trainer Camera Test"
MOVE_DISPLAY_SECONDS = 4.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Temporary local trainer test that writes punches into the active backend SQLite database."
    )
    parser.add_argument(
        "--camera-index",
        type=int,
        default=int(os.environ.get("BOXING_CAMERA_INDEX", "0")),
        help="Camera index to open. FaceTime is usually 0 on macOS.",
    )
    parser.add_argument("--width", type=int, default=1280, help="Requested camera width.")
    parser.add_argument("--height", type=int, default=720, help="Requested camera height.")
    parser.add_argument(
        "--list-cameras",
        action="store_true",
        help="Print AVFoundation device names and exit.",
    )
    return parser.parse_args()


def list_cameras() -> str:
    try:
        result = subprocess.run(
            ["ffmpeg", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return "ffmpeg is not installed, so camera listing is unavailable."
    lines = result.stderr.splitlines()
    relevant = [line for line in lines if "AVFoundation" in line or "FaceTime" in line or "Capture screen" in line]
    return "\n".join(relevant) if relevant else result.stderr.strip()


def open_camera(camera_index: int, width: int, height: int) -> cv2.VideoCapture:
    attempted_indices = [camera_index]
    if camera_index != 0:
        attempted_indices.append(0)

    attempts = []
    for index in attempted_indices:
        attempts.append((index, cv2.VideoCapture(index, cv2.CAP_AVFOUNDATION)))
        attempts.append((index, cv2.VideoCapture(index)))

    for index, cap in attempts:
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            print(f"Using camera index {index}.")
            return cap
        cap.release()

    raise RuntimeError(
        "Could not open the requested camera.\n"
        f"Tried indices: {attempted_indices}\n"
        "If index 0 fails, grant camera permission in System Settings > Privacy & Security > Camera.\n\n"
        f"Detected AVFoundation devices:\n{list_cameras()}"
    )


def decode_jpeg(frame_bytes: bytes) -> np.ndarray | None:
    if not frame_bytes:
        return None
    return cv2.imdecode(np.frombuffer(frame_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)


def put_text(frame: np.ndarray, text: str, origin: tuple[int, int], color: tuple[int, int, int], scale: float = 0.75) -> None:
    cv2.putText(frame, text, origin, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(frame, text, origin, cv2.FONT_HERSHEY_SIMPLEX, scale, color, 2, cv2.LINE_AA)


def draw_overlay(frame: np.ndarray, session_id: str, payload: dict, move_display_until: float) -> np.ndarray:
    display = frame.copy()
    trainer = payload.get("trainer") or {}
    move_target = payload.get("movement_target")
    action = payload.get("action")
    punch_type = payload.get("punch_type")
    confidence = payload.get("confidence")

    height, width, _ = display.shape
    overlay = display.copy()
    cv2.rectangle(overlay, (0, 0), (width, 150), (20, 20, 20), -1)
    cv2.rectangle(overlay, (0, height - 120), (width, height), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.62, display, 0.38, 0, display)

    put_text(display, f"Session: {session_id[:8]}", (20, 35), (255, 255, 255))
    put_text(display, f"State: {payload.get('state', 'UNKNOWN')}", (20, 70), (255, 255, 255))
    put_text(display, f"Total Punches: {trainer.get('total_punches', 0)}", (20, 105), (255, 255, 255))
    put_text(display, f"Punches Until Move: {max(3 - trainer.get('pending_punches', 0), 0)}", (20, 140), (0, 255, 255))

    detection_text = "None"
    if action and punch_type:
        detection_text = f"{action} {str(punch_type).upper()} ({float(confidence or 0):.2f})"
    put_text(display, f"Last Detection: {detection_text}", (20, height - 75), (180, 255, 180))
    put_text(display, "Keys: q quit", (20, height - 35), (220, 220, 220), scale=0.65)

    if move_target and time.time() < move_display_until:
        movement = move_target.get("movement", "MOVE")
        target = move_target.get("target", {})
        text = f"{movement} x={float(target.get('x', 0)):.2f} y={float(target.get('y', 0)):.2f}"
        cv2.rectangle(display, (width - 520, 20), (width - 20, 140), (15, 75, 15), -1)
        cv2.rectangle(display, (width - 520, 20), (width - 20, 140), (0, 255, 0), 2)
        put_text(display, "MOVE REQUEST", (width - 490, 55), (0, 255, 0), scale=0.9)
        put_text(display, text, (width - 490, 95), (255, 255, 255), scale=0.7)
        put_text(display, "Saved to sessions/events", (width - 490, 125), (190, 255, 190), scale=0.6)

    return display


def main() -> int:
    args = parse_args()
    if args.list_cameras:
        print(list_cameras())
        return 0

    session_manager = SessionManager()
    session = session_manager.create_session()
    print(f"Created trainer session {session.session_id} for user {session.username}.")
    print("Every detected punch is written into the active backend SQLite database.")

    cap = open_camera(args.camera_index, args.width, args.height)
    move_display_until = 0.0
    latest_payload: dict = {"state": session.state.value, "trainer": {"pending_punches": 0, "total_punches": 0}}

    try:
        while cap.isOpened():
            ok, frame = cap.read()
            if not ok:
                print("Camera read failed; stopping.")
                break

            success, encoded = cv2.imencode(".jpg", frame)
            if not success:
                continue

            latest_payload = session_manager.process_uploaded_frame(session.session_id, encoded.tobytes())
            stored_frame = decode_jpeg(session_manager.latest_frame(session.session_id) or b"")
            display_frame = stored_frame if stored_frame is not None else frame

            if latest_payload.get("trainer_event"):
                move_display_until = time.time() + MOVE_DISPLAY_SECONDS
                move_target = latest_payload["trainer_event"]["movement_target"]
                dispatch = latest_payload["trainer_event"].get("dispatch") or {}
                print(
                    "Move request:",
                    move_target.get("movement"),
                    move_target.get("target"),
                )
                if dispatch:
                    print("TCP dispatch:", dispatch)
            elif latest_payload.get("action") and latest_payload.get("punch_type"):
                print(
                    "Punch detected:",
                    latest_payload["action"],
                    str(latest_payload["punch_type"]).upper(),
                    f"{float(latest_payload.get('confidence', 0)):.2f}",
                )

            display_frame = draw_overlay(display_frame, session.session_id, latest_payload, move_display_until)
            cv2.imshow(WINDOW_NAME, display_frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()

    print(f"Trainer session saved as {session.session_id}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
