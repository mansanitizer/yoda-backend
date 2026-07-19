from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Optional

import cv2
import numpy as np
import torch
import torch.nn as nn
from ultralytics import YOLO

from app.core.state_machine import PunchSide


CONFIG = {
    "YOLO_MODEL_NAME": "yolo11m-pose.pt",
    "PUNCH_LSTM_MODEL_NAME": "punch_classifier.pth",
    "PUNCH_ACTIONS": ["jab", "cross", "hook", "uppercut"],
    "KEYPOINT_MAP": {
        "nose": 0,
        "left_eye": 1,
        "right_eye": 2,
        "left_ear": 3,
        "right_ear": 4,
        "left_shoulder": 5,
        "right_shoulder": 6,
        "left_elbow": 7,
        "right_elbow": 8,
        "left_wrist": 9,
        "right_wrist": 10,
        "left_hip": 11,
        "right_hip": 12,
        "left_knee": 13,
        "right_knee": 14,
        "left_ankle": 15,
        "right_ankle": 16,
    },
    "ACTION_KEYPOINTS": [
        "left_shoulder",
        "right_shoulder",
        "left_elbow",
        "right_elbow",
        "left_wrist",
        "right_wrist",
        "left_hip",
        "right_hip",
    ],
    "SEQUENCE_LENGTH": 25,
    "CONFIDENCE_THRESHOLD": 0.7,
    "KEYPOINT_CONF_THRESH": 0.5,
    "MIN_PUNCH_SPEED": 2.0,
    "DETECTION_COOLDOWN_SECONDS": 1.0,
}


class ActionClassifierLSTM(nn.Module):
    def __init__(self, input_size: int, hidden_size: int, num_layers: int, num_classes: int, dropout: float = 0.5):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=dropout)
        self.fc = nn.Linear(hidden_size, num_classes)
        self.hidden_size = hidden_size
        self.num_layers = num_layers

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        out, _ = self.lstm(x, (h0, c0))
        return self.fc(out[:, -1, :])


@dataclass
class DetectionResult:
    punch_type: str
    action: PunchSide
    confidence: float
    annotated_jpeg: bytes


def _normalize_keypoints(kps: np.ndarray, confs: np.ndarray) -> Optional[np.ndarray]:
    k_map = CONFIG["KEYPOINT_MAP"]
    ls_idx, rs_idx = k_map["left_shoulder"], k_map["right_shoulder"]
    if confs[ls_idx] < CONFIG["KEYPOINT_CONF_THRESH"] or confs[rs_idx] < CONFIG["KEYPOINT_CONF_THRESH"]:
        return None
    left_shoulder, right_shoulder = kps[ls_idx], kps[rs_idx]
    scale_dist = np.linalg.norm(left_shoulder - right_shoulder)
    if scale_dist < 1e-4:
        return None
    selected_indices = [k_map[name] for name in CONFIG["ACTION_KEYPOINTS"]]
    kps_subset = kps[selected_indices]
    confs_subset = confs[selected_indices]
    center_point = (left_shoulder + right_shoulder) / 2
    normalized_kps = np.zeros_like(kps_subset)
    valid_mask = confs_subset > CONFIG["KEYPOINT_CONF_THRESH"]
    normalized_kps[valid_mask] = (kps_subset[valid_mask] - center_point) / scale_dist
    return normalized_kps.flatten()


def _calculate_punch_speed(buffer: deque) -> float:
    if len(buffer) < 5:
        return 0.0
    k_map = CONFIG["KEYPOINT_MAP"]
    recent_frames = list(buffer)[-5:]
    speeds = []
    for wrist_key in ["left_wrist", "right_wrist"]:
        wrist_idx = k_map[wrist_key]
        positions = [
            frame["raw_kps"][wrist_idx]
            for frame in recent_frames
            if frame["confs"][wrist_idx] > CONFIG["KEYPOINT_CONF_THRESH"]
        ]
        if len(positions) >= 2:
            total_distance = sum(np.linalg.norm(positions[i + 1] - positions[i]) for i in range(len(positions) - 1))
            speeds.append(total_distance / len(positions))
    return max(speeds) if speeds else 0.0


def _infer_punch_side(buffer: deque) -> PunchSide:
    if len(buffer) < 2:
        return PunchSide.NONE
    k_map = CONFIG["KEYPOINT_MAP"]
    start_frame = buffer[0]
    end_frame = buffer[-1]

    def wrist_delta(name: str) -> float:
        idx = k_map[name]
        if (
            start_frame["confs"][idx] > CONFIG["KEYPOINT_CONF_THRESH"]
            and end_frame["confs"][idx] > CONFIG["KEYPOINT_CONF_THRESH"]
        ):
            return float(np.linalg.norm(end_frame["raw_kps"][idx] - start_frame["raw_kps"][idx]))
        return 0.0

    left_delta = wrist_delta("left_wrist")
    right_delta = wrist_delta("right_wrist")
    if left_delta <= 0.0 and right_delta <= 0.0:
        return PunchSide.NONE
    return PunchSide.LEFT if left_delta > right_delta else PunchSide.RIGHT


def _draw_overlay(frame: np.ndarray, detection: Optional[dict], label: Optional[str]) -> bytes:
    output = frame.copy()
    if detection:
        box = detection["box"].astype(int)
        kps = detection["kps"]
        confs = detection["confs"]
        cv2.rectangle(output, (box[0], box[1]), (box[2], box[3]), (0, 255, 0), 2)
        for name in ["left_wrist", "right_wrist", "left_elbow", "right_elbow", "left_shoulder", "right_shoulder"]:
            idx = CONFIG["KEYPOINT_MAP"][name]
            if confs[idx] > CONFIG["KEYPOINT_CONF_THRESH"]:
                point = (int(kps[idx][0]), int(kps[idx][1]))
                cv2.circle(output, point, 8, (0, 255, 255), -1)
        if label:
            cv2.putText(output, label, (box[0], max(40, box[1] - 20)), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
    success, encoded = cv2.imencode(".jpg", output)
    return bytearray(encoded) if success else b""


class SharedModels:
    _loaded = False
    _lock = Lock()
    device = "cpu"
    yolo_model: YOLO
    punch_model: ActionClassifierLSTM

    @classmethod
    def load(cls) -> None:
        with cls._lock:
            if cls._loaded:
                return
            app_root = Path(__file__).resolve().parents[1]
            if torch.cuda.is_available():
                cls.device = "cuda"
            elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
                cls.device = "mps"
            else:
                cls.device = "cpu"
            cls.yolo_model = YOLO(app_root / CONFIG["YOLO_MODEL_NAME"])
            input_size = len(CONFIG["ACTION_KEYPOINTS"]) * 2
            cls.punch_model = ActionClassifierLSTM(input_size, 128, 2, len(CONFIG["PUNCH_ACTIONS"])).to(cls.device)
            cls.punch_model.load_state_dict(
                torch.load(app_root / CONFIG["PUNCH_LSTM_MODEL_NAME"], map_location=cls.device)
            )
            cls.punch_model.eval()
            cls._loaded = True


class SessionDetector:
    def __init__(self) -> None:
        SharedModels.load()
        self.buffer = deque(maxlen=CONFIG["SEQUENCE_LENGTH"])
        self.last_detection_time = 0.0

    def process_frame(self, frame: np.ndarray) -> tuple[Optional[DetectionResult], bytes]:
        yolo_results = SharedModels.yolo_model(frame, verbose=False, device=SharedModels.device)
        current_detection = None
        if yolo_results and yolo_results[0].boxes is not None and len(yolo_results[0].boxes) > 0:
            boxes = yolo_results[0].boxes.xyxy.cpu().numpy()
            keypoints_list = yolo_results[0].keypoints.data.cpu().numpy()
            if len(boxes) > 0 and len(keypoints_list) > 0:
                current_detection = {
                    "kps": keypoints_list[0][:, :2],
                    "confs": keypoints_list[0][:, 2],
                    "box": boxes[0],
                }
                norm_kps = _normalize_keypoints(current_detection["kps"], current_detection["confs"])
                if norm_kps is not None:
                    self.buffer.append(
                        {
                            "norm_kps": norm_kps,
                            "raw_kps": current_detection["kps"].copy(),
                            "confs": current_detection["confs"].copy(),
                            "timestamp": cv2.getTickCount() / cv2.getTickFrequency(),
                        }
                    )

        detection_result = None
        label = None
        now = cv2.getTickCount() / cv2.getTickFrequency()
        if (
            len(self.buffer) == CONFIG["SEQUENCE_LENGTH"]
            and now - self.last_detection_time > CONFIG["DETECTION_COOLDOWN_SECONDS"]
            and _calculate_punch_speed(self.buffer) > CONFIG["MIN_PUNCH_SPEED"]
        ):
            sequence = np.array([frame_data["norm_kps"] for frame_data in self.buffer])
            sequence_tensor = torch.tensor(sequence, dtype=torch.float32).unsqueeze(0).to(SharedModels.device)
            with torch.no_grad():
                punch_output = SharedModels.punch_model(sequence_tensor)
                punch_conf, punch_idx = torch.max(torch.softmax(punch_output, dim=1), 1)
            confidence = float(punch_conf.item())
            if confidence > CONFIG["CONFIDENCE_THRESHOLD"]:
                punch_type = CONFIG["PUNCH_ACTIONS"][punch_idx.item()]
                action = _infer_punch_side(self.buffer)
                label = f"{action.value} {punch_type.upper()}" if action != PunchSide.NONE else punch_type.upper()
                annotated = _draw_overlay(frame, current_detection, label)
                detection_result = DetectionResult(
                    punch_type=punch_type,
                    action=action,
                    confidence=confidence,
                    annotated_jpeg=annotated,
                )
                self.last_detection_time = now

        debug_jpeg = detection_result.annotated_jpeg if detection_result else _draw_overlay(frame, current_detection, label)
        return detection_result, debug_jpeg
