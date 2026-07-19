from __future__ import annotations

import socket
from typing import Any


CONTROL_HOST = "127.0.0.1"
CONTROL_PORT = 65433


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(value, maximum))


def movement_target_to_commands(movement_target: dict[str, Any]) -> list[str]:
    movement = str(movement_target.get("movement", "ADVANCE")).upper()
    target = movement_target.get("target", {}) or {}
    x = float(target.get("x", 0.0))
    y = float(target.get("y", 0.0))
    distance_m = float(movement_target.get("distance_m", 0.0))

    linear_strength = _clamp(max(15, round(max(abs(x), distance_m) * 100)), 15, 90)
    lateral_strength = _clamp(max(15, round(max(abs(y), distance_m * 0.8) * 100)), 15, 75)

    if movement == "ADVANCE":
        return [f"F{linear_strength}"]
    if movement == "RETREAT":
        return [f"B{linear_strength}"]
    if movement == "SLIP_LEFT":
        return [f"L{lateral_strength}"]
    if movement == "SLIP_RIGHT":
        return [f"R{lateral_strength}"]
    if movement == "CIRCLE_LEFT":
        return [f"L{lateral_strength}", f"F{_clamp(linear_strength // 2, 15, 45)}"]
    if movement == "CIRCLE_RIGHT":
        return [f"R{lateral_strength}", f"F{_clamp(linear_strength // 2, 15, 45)}"]

    if abs(x) >= abs(y):
        return [f"F{linear_strength}" if x >= 0 else f"B{linear_strength}"]
    return [f"L{lateral_strength}" if y >= 0 else f"R{lateral_strength}"]


def dispatch_movement_target(movement_target: dict[str, Any]) -> dict[str, Any]:
    commands = movement_target_to_commands(movement_target)
    acknowledgements: list[str] = []

    with socket.create_connection((CONTROL_HOST, CONTROL_PORT), timeout=1.5) as sock:
        for command in commands:
            sock.sendall(f"{command}\n".encode("utf-8"))
            acknowledgements.append(sock.recv(1024).decode("utf-8").strip())

    return {
        "host": CONTROL_HOST,
        "port": CONTROL_PORT,
        "commands": commands,
        "acknowledgements": acknowledgements,
    }
