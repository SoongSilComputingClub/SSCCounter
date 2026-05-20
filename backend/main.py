from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os
from datetime import datetime
import cv2
import numpy as np
from ultralytics import YOLO

app = FastAPI(title="SSCCounter API", version="2.1")

app.mount("/data", StaticFiles(directory="../frontend/data"), name="data")
app.mount("/css", StaticFiles(directory="../frontend/css"), name="css")
app.mount("/js", StaticFiles(directory="../frontend/js"), name="js")

# ---------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용 (개발 단계에서는 편리하지만, 배포 시에는 보안을 위해 특정 도메인만 허용하는 것이 좋습니다)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 이미지를 임시로 저장할 디렉토리 설정
UPLOAD_DIR = "uploaded_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# YOLO 모델 로드 (yolo_inference.py에서 가져옴)
print("Loading YOLO model...")
model = YOLO("yolov8n.pt")
print("YOLO model loaded successfully.")

def infer_people_count(frame):
    results = model.predict(source=frame, conf=0.3, classes=[0], imgsz=416, verbose=False)
    return (results[0].boxes.cls == 0).sum().item()

# ---------------------------------------------

SHOULD_CAPTURE = False
LATEST_COUNT = 0  # 가장 최근에 측정된 인원수

@app.post("/api/v2/test/trigger")
async def trigger_capture():
    """
    [Swagger UI용] 이 API를 호출하면 ESP32에게 사진을 찍으라는 명령을 내립니다.
    """
    global SHOULD_CAPTURE
    SHOULD_CAPTURE = True
    return {"status": "success", "message": "Capture command issued to ESP32."}

@app.get("/api/v2/device/command")
async def get_device_command():
    """
    [ESP32용] ESP32가 주기적으로 이 API를 호출하여 명령이 있는지 확인합니다.
    """
    global SHOULD_CAPTURE
    if SHOULD_CAPTURE:
        SHOULD_CAPTURE = False # 명령을 전달했으므로 다시 대기 상태로 변경
        return {"command": "capture"}
    return {"command": "idle"}

# --------------------------------------------

@app.get("/")
async def root():
    """
    브라우저로 서버 주소에 접속하면 index.html 웹페이지를 띄워줍니다.
    """
    return FileResponse("../frontend/index.html")

@app.get("/api/v2/count/current")
async def get_current_count():
    """
    [프론트엔드용] 현재 동아리방 인원수를 반환합니다.
    """
    return {"count": LATEST_COUNT}

@app.get("/api/v2/stats/today")
async def get_today_stats():
    """
    [프론트엔드용] 오늘 시간대별 인원 통계를 반환합니다. (현재는 더미 데이터)
    추후 PostgreSQL DB 연동 시 쿼리 결과를 반환하도록 수정해야 합니다.
    """
    current_hour = datetime.now().hour
    today_data = []
    # 9시부터 현재 시간까지의 가짜 데이터 생성
    for h in range(9, 23):
        if h <= current_hour:
            # 임시로 LATEST_COUNT 근처의 랜덤 값 생성 (나중에 DB 연동 시 제거)
            today_data.append({"hour": h, "count": max(0, LATEST_COUNT + np.random.randint(-2, 3))})
    
    if not today_data:
        today_data.append({"hour": 9, "count": 0})
        
    return today_data

@app.get("/api/v2/stats/weekly")
async def get_weekly_stats():
    """
    [프론트엔드용] 최근 4주간의 요일별 평균 통계를 반환합니다. (현재는 더미 데이터)
    """
    return {
        "mon": [2, 3, 5, 8, 6, 4, 0, 0, 8, 5, 3, 2, 1, 1],
        "tue": [1, 2, 4, 6, 0, 0, 0, 0, 3, 7, 4, 3, 2, 1],
        "wed": [3, 4, 6, 9, 11, 14, 15, 13, 9, 6, 4, 2, 1, 1],
        "thu": [2, 3, 5, 7, 12, 16, 18, 15, 11, 8, 5, 3, 2, 1],
        "fri": [1, 2, 3, 5, 8, 10, 12, 9, 7, 4, 3, 2, 1, 0]
    }

# --------------------------------------------

@app.post("/api/v2/device/upload")
async def upload_image(file: UploadFile = File(...)):
    global LATEST_COUNT

    try:
        # 현재 시간을 파일명으로 사용하여 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = file.filename.split('.')[-1]
        file_path = os.path.join(UPLOAD_DIR, f"{timestamp}.{file_extension}")

        content = await file.read()
        
        # 파일 저장
        with open(file_path, "wb") as buffer:
            buffer.write(content)
            
        nparr = np.frombuffer(content, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        people_count = 0
        if frame is not None:
            people_count = infer_people_count(frame)
            LATEST_COUNT = people_count
            print(f"[{timestamp}] Inference Result: {people_count} people detected.")
        else:
            print("Failed to decode image for YOLO inference.")

        return {
            "status": "success", 
            "message": "Image processed successfully", 
            "file_path": file_path,
            "detected_count": people_count
        }
    except Exception as e:
        print(f"Error during upload/inference: {str(e)}")
        return {"status": "error", "message": str(e)}