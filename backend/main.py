from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os
from datetime import datetime
import cv2
import numpy as np
from ultralytics import YOLO
import time
from decimal import Decimal
import psycopg
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from psycopg_pool import ConnectionPool

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

db_pool = None

@asynccontextmanager
async def lifespan(app:FastAPI):
    global db_pool

    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")
    
    db_pool = ConnectionPool(
        conninfo=DATABASE_URL,
        min_size=1,
        max_size=10,
        open=True,
    )

    try:
        yield
    finally:
        db_pool.close()

app = FastAPI(title="SSCCounter API", version="2.1", lifespan=lifespan)

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

# YOLO 모델 로드 (yolo_inference.py에서 가져옴)
print("Loading YOLO model...")
model = YOLO("yolov8n.pt")
print("YOLO model loaded successfully.")

def infer_people_count(frame):
    results = model.predict(source=frame, conf=0.3, classes=[0], imgsz=416, verbose=False)
    return (results[0].boxes.cls == 0).sum().item()

# ---------------------------------------------

def get_db_connection():
    if db_pool is None:
        raise RuntimeError("Database connection pool is not initialized")
    return db_pool.connection()

def to_float(value):
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return value

def get_current_status_from_db():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT current_people_count, updated_at, today_max_people_count, today_avg_people_count
                FROM dashboard.current_status
                WHERE id = 1
                """
            )
            row = cur.fetchone()
        
    if row is None:
        return {
            "count": 0,
            "updated_at": None,
            "today_max_count": 0,
            "today_avg_count": 0.0
        }
    
    return {
        "count": row[0],
        "updated_at": row[1].isoformat() if row[1] else None,
        "today_max_count": row[2],
        "today_avg_count": to_float(row[3])
    }

def save_failed_inference(error_message: str, trigger_type: str = "scheduled", inference_time_ms: int | None = None):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO admin.capture_logs (people_count, status, trigger_type, inference_time_ms, error_message)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    None,
                    "failed",
                    trigger_type,
                    inference_time_ms,
                    error_message
                )
            )

def save_successful_inference(people_count: int, trigger_type: str = "scheduled", inference_time_ms: int | None = None):
    """
    YOLO 추론 성공 결과를 admin raw log와 dashboard summary tables에 반영합니다.

    처리 순서:
    1. admin.capture_logs insert
    2. dashboard.current_status update
    3. dashboard.today_hourly_stats update
    4. dashboard.daily_stats update
    5. dashboard.weekday_hourly_stats update
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 1. 관리자용 raw log 저장
            cur.execute(
                """
                INSERT INTO admin.capture_logs (people_count, status, trigger_type, inference_time_ms)
                VALUES (%s, %s, %s, %s)
                RETURNING measured_at
                """,
                (
                    people_count,
                    "success",
                    trigger_type,
                    inference_time_ms
                )
            )
            measured_at = cur.fetchone()[0]

            # 2. dashboard.current_status 갱신
            cur.execute(
                """
                WITH today_summary AS (
                    SELECT
                        COALESCE(MAX(people_count), 0) AS today_max_people_count,
                        COALESCE(ROUND(AVG(people_count)::numeric, 2), 0) AS today_avg_people_count
                    FROM admin.capture_logs
                    WHERE status = 'success'
                      AND measured_at >= date_trunc('day', now())
                      AND measured_at < date_trunc('day', now()) + interval '1 day'
                )
                INSERT INTO dashboard.current_status (
                    id,
                    current_people_count,
                    updated_at,
                    today_max_people_count,
                    today_avg_people_count
                )
                SELECT
                    1,
                    %s,
                    %s,
                    today_max_people_count,
                    today_avg_people_count
                FROM today_summary
                ON CONFLICT (id)
                DO UPDATE SET
                    current_people_count = EXCLUDED.current_people_count,
                    updated_at = EXCLUDED.updated_at,
                    today_max_people_count = EXCLUDED.today_max_people_count,
                    today_avg_people_count = EXCLUDED.today_avg_people_count
                """,
                (
                    people_count,
                    measured_at
                )
            )

            # 3. dashboard.today_hourly_stats 갱신
            cur.execute(
                """
                WITH hourly AS (
                    SELECT
                        current_date AS stat_date,
                        EXTRACT(HOUR FROM measured_at)::int AS hour,
                        ROUND(AVG(people_count)::numeric, 2) AS avg_people_count,
                        MAX(people_count) AS max_people_count,
                        COUNT(*) AS sample_count
                    FROM admin.capture_logs
                    WHERE status = 'success'
                      AND measured_at >= date_trunc('day', now())
                      AND measured_at < date_trunc('day', now()) + interval '1 day'
                    GROUP BY stat_date, hour
                )
                INSERT INTO dashboard.today_hourly_stats (
                    stat_date,
                    hour,
                    avg_people_count,
                    max_people_count,
                    sample_count,
                    updated_at
                )
                SELECT
                    stat_date,
                    hour,
                    avg_people_count,
                    max_people_count,
                    sample_count,
                    now()
                FROM hourly
                ON CONFLICT (stat_date, hour)
                DO UPDATE SET
                    avg_people_count = EXCLUDED.avg_people_count,
                    max_people_count = EXCLUDED.max_people_count,
                    sample_count = EXCLUDED.sample_count,
                    updated_at = EXCLUDED.updated_at
                """
            )

            # 4. dashboard.daily_stats 갱신
            cur.execute(
                """
                WITH base AS (
                    SELECT
                        people_count,
                        measured_at,
                        EXTRACT(HOUR FROM measured_at)::int AS hour
                    FROM admin.capture_logs
                    WHERE status = 'success'
                      AND measured_at >= date_trunc('day', now())
                      AND measured_at < date_trunc('day', now()) + interval '1 day'
                ),
                hourly AS (
                    SELECT
                        hour,
                        ROUND(AVG(people_count)::numeric, 2) AS avg_people_count
                    FROM base
                    WHERE hour BETWEEN 9 AND 22
                    GROUP BY hour
                ),
                summary AS (
                    SELECT
                        current_date AS stat_date,
                        COALESCE(ROUND(AVG(people_count)::numeric, 2), 0) AS avg_people_count,
                        COALESCE(MAX(people_count), 0) AS max_people_count,
                        COALESCE(MIN(people_count), 0) AS min_people_count,
                        COUNT(*) AS sample_count
                    FROM base
                ),
                peak AS (
                    SELECT hour AS peak_hour
                    FROM hourly
                    ORDER BY avg_people_count DESC, hour ASC
                    LIMIT 1
                ),
                quiet AS (
                    SELECT hour AS quiet_hour
                    FROM hourly
                    ORDER BY avg_people_count ASC, hour ASC
                    LIMIT 1
                )
                INSERT INTO dashboard.daily_stats (
                    stat_date,
                    avg_people_count,
                    max_people_count,
                    min_people_count,
                    peak_hour,
                    quiet_hour,
                    sample_count,
                    updated_at
                )
                SELECT
                    summary.stat_date,
                    summary.avg_people_count,
                    summary.max_people_count,
                    summary.min_people_count,
                    peak.peak_hour,
                    quiet.quiet_hour,
                    summary.sample_count,
                    now()
                FROM summary
                LEFT JOIN peak ON true
                LEFT JOIN quiet ON true
                ON CONFLICT (stat_date)
                DO UPDATE SET
                    avg_people_count = EXCLUDED.avg_people_count,
                    max_people_count = EXCLUDED.max_people_count,
                    min_people_count = EXCLUDED.min_people_count,
                    peak_hour = EXCLUDED.peak_hour,
                    quiet_hour = EXCLUDED.quiet_hour,
                    sample_count = EXCLUDED.sample_count,
                    updated_at = EXCLUDED.updated_at
                """
            )

            # 5. dashboard.weekday_hourly_stats 갱신
            cur.execute(
                """
                WITH weekday_hourly AS (
                    SELECT
                        EXTRACT(ISODOW FROM measured_at)::int AS weekday,
                        EXTRACT(HOUR FROM measured_at)::int AS hour,
                        ROUND(AVG(people_count)::numeric, 2) AS avg_people_count,
                        MAX(people_count) AS max_people_count,
                        COUNT(*) AS sample_count
                    FROM admin.capture_logs
                    WHERE status = 'success'
                      AND measured_at >= now() - interval '4 weeks'
                      AND EXTRACT(ISODOW FROM measured_at)::int BETWEEN 1 AND 5
                      AND EXTRACT(HOUR FROM measured_at)::int BETWEEN 9 AND 22
                    GROUP BY weekday, hour
                )
                INSERT INTO dashboard.weekday_hourly_stats (
                    weekday,
                    hour,
                    avg_people_count,
                    max_people_count,
                    sample_count,
                    updated_at
                )
                SELECT
                    weekday,
                    hour,
                    avg_people_count,
                    max_people_count,
                    sample_count,
                    now()
                FROM weekday_hourly
                ON CONFLICT (weekday, hour)
                DO UPDATE SET
                    avg_people_count = EXCLUDED.avg_people_count,
                    max_people_count = EXCLUDED.max_people_count,
                    sample_count = EXCLUDED.sample_count,
                    updated_at = EXCLUDED.updated_at
                """
            )

def get_today_stats_from_db():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT hours.hour, COALESCE(stats.avg_people_count, 0) AS count
                FROM generate_series(9, 22) AS hours(hour)
                LEFT JOIN dashboard.today_hourly_stats AS stats
                  ON stats.hour = hours.hour
                 AND stats.stat_date = current_date
                ORDER BY hours.hour
                """
            )
            rows = cur.fetchall()

    return [
        {
            "hour": row[0],
            "count": row[1]
        }
        for row in rows
    ]

def get_weekly_stats_from_db():
    day_key_map = {
        1: "mon",
        2: "tue",
        3: "wed",
        4: "thu",
        5: "fri"
    }

    weekly_stats = {
        "mon": [0] * 14,
        "tue": [0] * 14,
        "wed": [0] * 14,
        "thu": [0] * 14,
        "fri": [0] * 14
    }

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    weekday,
                    hour,
                    avg_people_count
                FROM dashboard.weekday_hourly_stats
                WHERE weekday BETWEEN 1 AND 5
                  AND hour BETWEEN 9 AND 22
                ORDER BY weekday, hour
                """
            )
            rows = cur.fetchall()
    for weekday, hour, avg_people_count in rows:
        day_key = day_key_map.get(weekday)
        if not day_key:
            continue
        
        index = hour - 9
        if 0 <= index < 14:
            weekly_stats[day_key][index] = to_float(avg_people_count)

    return weekly_stats

# ---------------------------------------------

SHOULD_CAPTURE = False

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
    return get_current_status_from_db()

@app.get("/api/v2/stats/today")
async def get_today_stats():
    """
    [프론트엔드용] 오늘 시간대별 인원 통계를 반환합니다.
    """
    return get_today_stats_from_db()

@app.get("/api/v2/stats/weekly")
async def get_weekly_stats():
    """
    [프론트엔드용] 평일 시간대별 평균 통계를 반환합니다.
    """
    return get_weekly_stats_from_db()

# --------------------------------------------

@app.post("/api/v2/device/upload")
async def upload_image(file: UploadFile = File(...)):
    """
    [ESP32용] ESP32-CAM이 업로드한 이미지를 서버 메모리에서만 처리합니다.

    처리 흐름:
    1. 업로드된 이미지 bytes 읽기
    2. OpenCV로 JPEG 디코딩
    3. YOLO로 사람 수 추론
    4. 최신 인원 수 갱신
    5. 이미지 파일은 저장하지 않고 함수 종료와 함께 폐기
    """
    measured_at = datetime.now()

    try:
        # 업로드된 이미지 bytes를 메모리에서 읽음
        content = await file.read()

        # bytes -> numpy array -> OpenCV frame
        nparr = np.frombuffer(content, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            error_message = "Failed to decode image."
            print(f"[{measured_at}] {error_message}")

            save_failed_inference(error_message=error_message, trigger_type="scheduled")

            return {
                "status": "error",
                "message": error_message
            }

        inference_start = time.perf_counter()
        people_count = infer_people_count(frame)
        inference_time_ms = int((time.perf_counter() - inference_start) * 1000)

        save_successful_inference(people_count=people_count, trigger_type="scheduled", inference_time_ms=inference_time_ms)

        print(f"[{measured_at}] Inference Result: {people_count} people detected. Inference Time: {inference_time_ms} ms")

        return {
            "status": "success",
            "message": "Image processed successfully",
            "detected_count": people_count
        }
    except Exception as e:
        error_message = str(e)
        print(f"Error during upload/inference: {error_message}")

        try: 
            save_failed_inference(error_message=error_message, trigger_type="scheduled")
        except Exception as db_error:
            print(f"Failed to save error log to DB: {str(db_error)}")

        return {"status": "error", "message": error_message}