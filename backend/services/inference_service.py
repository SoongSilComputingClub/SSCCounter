import time

import cv2
import numpy as np
from ultralytics import YOLO

print("Loading YOLO model...")
_model = YOLO("yolov8n.pt")
print("YOLO model loaded successfully.")


def decode_image(content: bytes) -> np.ndarray | None:
    """JPEG 이미지 바이트를 OpenCV frame으로 디코딩합니다."""
    image_buffer = np.frombuffer(content, dtype=np.uint8)
    return cv2.imdecode(image_buffer, cv2.IMREAD_COLOR)


def infer_people_count(frame: np.ndarray) -> int:
    """OpenCV frame에서 사람 수를 추론합니다."""
    results = _model.predict(
        source=frame,
        conf=0.3,
        classes=[0],
        imgsz=416,
        verbose=False,
    )

    return int((results[0].boxes.cls == 0).sum().item())


def run_inference(frame: np.ndarray) -> tuple[int, int]:
    """사람 수를 추론하고 소요 시간을 밀리초 단위로 반환합니다."""
    inference_start = time.perf_counter()
    people_count = infer_people_count(frame)
    inference_time_ms = int((time.perf_counter() - inference_start) * 1000)

    return people_count, inference_time_ms
