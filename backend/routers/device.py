from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, File, UploadFile

from services.inference_service import decode_image, run_inference
from services.stats_service import (
    save_failed_inference,
    save_successful_inference,
)

router = APIRouter(prefix="/api/v2", tags=["device"])

_should_capture = False


@router.post("/test/trigger")
async def trigger_capture():
    """
    [Swagger UI용] ESP32에 사진 촬영 명령을 전달합니다.
    """
    global _should_capture

    _should_capture = True

    return {
        "status": "success",
        "message": "Capture command issued to ESP32.",
    }


@router.get("/device/command")
async def get_device_command():
    """
    [ESP32용] ESP32가 촬영 명령을 확인합니다.
    """
    global _should_capture

    if _should_capture:
        _should_capture = False
        return {"command": "capture"}

    return {"command": "idle"}


@router.post("/device/upload")
async def upload_image(file: Annotated[UploadFile, File(...)]):
    """
    [ESP32용] 업로드된 이미지를 메모리에서 처리하고 추론 결과를 저장합니다.
    """
    measured_at = datetime.now()

    try:
        content = await file.read()
        frame = decode_image(content)

        if frame is None:
            error_message = "Failed to decode image."
            print(f"[{measured_at}] {error_message}")

            save_failed_inference(
                error_message=error_message,
                trigger_type="scheduled",
            )

            return {
                "status": "error",
                "message": error_message,
            }

        people_count, inference_time_ms = run_inference(frame)

        save_successful_inference(
            people_count=people_count,
            trigger_type="scheduled",
            inference_time_ms=inference_time_ms,
        )

        print(
            f"[{measured_at}] Inference Result: "
            f"{people_count} people detected. "
            f"Inference Time: {inference_time_ms} ms"
        )

        return {
            "status": "success",
            "message": "Image processed successfully",
            "detected_count": people_count,
        }
    except Exception as error:
        error_message = str(error)
        print(f"Error during upload/inference: {error_message}")

        try:
            save_failed_inference(
                error_message=error_message,
                trigger_type="scheduled",
            )
        except Exception as db_error:
            print(f"Failed to save error log to DB: {db_error}")

        return {
            "status": "error",
            "message": error_message,
        }
