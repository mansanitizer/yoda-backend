from __future__ import annotations

import math
import random
from collections.abc import Sequence


MOVEMENT_PROFILES = {
    "ADVANCE": {
        "heading_range_deg": (-20.0, 20.0),
        "distance_range_m": (0.35, 0.8),
        "orientation_bias_deg": 180.0,
        "duration_s": 2.2,
        "weight": 1.0,
    },
    "RETREAT": {
        "heading_range_deg": (155.0, 205.0),
        "distance_range_m": (0.45, 0.9),
        "orientation_bias_deg": 0.0,
        "duration_s": 2.5,
        "weight": 0.9,
    },
    "SLIP_LEFT": {
        "heading_range_deg": (80.0, 120.0),
        "distance_range_m": (0.25, 0.6),
        "orientation_bias_deg": 270.0,
        "duration_s": 1.8,
        "weight": 1.1,
    },
    "SLIP_RIGHT": {
        "heading_range_deg": (-120.0, -80.0),
        "distance_range_m": (0.25, 0.6),
        "orientation_bias_deg": 90.0,
        "duration_s": 1.8,
        "weight": 1.1,
    },
    "CIRCLE_LEFT": {
        "heading_range_deg": (35.0, 75.0),
        "distance_range_m": (0.4, 0.85),
        "orientation_bias_deg": 315.0,
        "duration_s": 2.7,
        "weight": 1.2,
    },
    "CIRCLE_RIGHT": {
        "heading_range_deg": (-75.0, -35.0),
        "distance_range_m": (0.4, 0.85),
        "orientation_bias_deg": 45.0,
        "duration_s": 2.7,
        "weight": 1.2,
    },
}


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def _build_movement_target(movement_name: str, radius_m: float) -> dict:
    profile = MOVEMENT_PROFILES[movement_name]
    distance_min, distance_max = profile["distance_range_m"]
    heading_min, heading_max = profile["heading_range_deg"]
    distance = random.uniform(distance_min, min(distance_max, radius_m))
    heading_deg = random.uniform(heading_min, heading_max)
    heading_rad = math.radians(heading_deg)
    orientation_deg = (profile["orientation_bias_deg"] + random.uniform(-18.0, 18.0)) % 360.0
    x = round(distance * math.cos(heading_rad), 3)
    y = round(distance * math.sin(heading_rad), 3)
    return {
        "command": "MOVE",
        "algorithm": "three_punch_reaction_v1",
        "movement": movement_name,
        "radius_m": radius_m,
        "distance_m": round(distance, 3),
        "heading_deg": round(heading_deg, 2),
        "target": {"x": x, "y": y},
        "orientation_deg": round(orientation_deg, 2),
        "duration_s": profile["duration_s"],
    }


def _weighted_movement_choice(recent_movements: Sequence[str]) -> str:
    weights: list[float] = []
    movement_names = list(MOVEMENT_PROFILES.keys())
    last = recent_movements[-1] if recent_movements else None
    last_two = tuple(recent_movements[-2:]) if len(recent_movements) >= 2 else ()

    for movement_name in movement_names:
        weight = MOVEMENT_PROFILES[movement_name]["weight"]
        if movement_name == last:
            weight *= 0.25
        if len(last_two) == 2 and last_two[0] == last_two[1] == movement_name:
            weight = 0.0
        if last == "ADVANCE" and movement_name == "RETREAT":
            weight *= 1.25
        if last == "RETREAT" and movement_name == "ADVANCE":
            weight *= 1.25
        weights.append(_clamp(weight, 0.0, 10.0))

    if not any(weights):
        return random.choice(movement_names)
    return random.choices(movement_names, weights=weights, k=1)[0]


def random_movement_target(radius_m: float = 1.0, recent_movements: Sequence[str] | None = None) -> dict:
    movement_name = _weighted_movement_choice(recent_movements or [])
    return _build_movement_target(movement_name, radius_m)
