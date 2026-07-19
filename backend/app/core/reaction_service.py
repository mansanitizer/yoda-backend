from __future__ import annotations

import math
import random


def random_movement_target(radius_m: float = 1.0) -> dict:
    distance = random.uniform(0.0, radius_m)
    heading = random.uniform(0.0, 2.0 * math.pi)
    orientation_deg = random.uniform(0.0, 360.0)
    x = round(distance * math.cos(heading), 3)
    y = round(distance * math.sin(heading), 3)
    return {
        "radius_m": radius_m,
        "target": {"x": x, "y": y},
        "orientation_deg": round(orientation_deg, 2),
    }
