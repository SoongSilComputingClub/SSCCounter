# SSCCounter Backend (v2.1)

SSCC 동아리방 실시간 인원 카운팅 시스템(`SSCCounter`)의 백엔드 API 서버 및 정적 웹 서빙을 담당하는 저장소입니다. 

본 백엔드는 ESP32-CAM 하드웨어 기기로부터 주기적으로 촬영된 이미지를 전송받아 인공지능(YOLOv8) 모델을 통해 실시간으로 사람을 감지하고 동아리방 내 실시간 인원수를 추론합니다. 또한, 프론트엔드 웹 서비스가 원활하게 동작할 수 있도록 최신 상태 데이터 및 통계 데이터를 제공하며, 프론트엔드 정적 파일을 직접 서빙하는 단일 통합 웹 서버 역할을 수행합니다.

---

## 🛠 기술 스택

- **Framework**: FastAPI (Python 기반 고성능 비동기 웹 프레임워크)
- **AI/Inference**: Ultralytics YOLOv8 (YOLOv8n-lightweight 모델 사용)
- **Image Processing**: OpenCV (Open Source Computer Vision Library), NumPy
- **Server/ASGI**: Uvicorn (ASGI 서버 선언 및 구동)

---

## 📂 프로젝트 구조 (전체 디렉토리 구성 예시)

백엔드 서버는 프론트엔드 정적 자산 폴더(`frontend`)와 상위 폴더를 공유하는 구조로 설계되어 있습니다. 경로 참조 시 유의하시기 바랍니다.

```text
📂 SSCCounter/
├── 📂 backend/
│   ├── main.py              # 백엔드 코어 및 API 라우팅 정의
│   ├── yolov8n.pt           # YOLOv8 경량 모델 파일 (최초 실행 시 자동 다운로드)
│   └── 📂 uploaded_images/  # ESP32-CAM이 업로드한 정적 이미지 임시 저장소 (자동 생성)
└── 📂 frontend/
    ├── index.html           # 메인 대시보드 웹 화면
    ├── 📂 css/              # 스타일시트 (base.css, components.css, darkmode.css)
    ├── 📂 js/               # 스크립트 (data.js, chart.js, app.js, tailwind.config.js)
    └── 📂 data/             # 정적 JSON 데이터 (developers.json)
```

---

## 🚀요구 사항 및 설치 가이드

### 1. 필수 구성 요소

본 프로젝트를 실행하려면 시스템에 **Python 3.8 이상**과 **pip**가 설치되어 있어야 합니다. 또한 인공지능 추론 및 이미지 처리를 위한 기본 네이티브 라이브러리(OpenCV 등) 의존성이 필요합니다.

### 2. 가상환경 생성 및 활성화

프로젝트의 종속성이 로컬 시스템과 충돌하지 않도록 가상환경을 생성하는 것을 강력히 권장합니다.

```bash
# backend 폴더로 이동
cd backend

# 가상환경 생성 (venv)
python -m venv venv

# 가상환경 활성화 (Windows)
.\venv\Scripts\activate

# 가상환경 활성화 (Linux / macOS)
source venv/bin/activate
```

### 3. 필수 패키지 의존성 설치

백엔드 구동에 필요한 핵심 패키지들을 설치합니다.

```bash
pip install fastapi uvicorn ultralytics opencv-python numpy
```

---

## 💻 서버 실행 방법

가상환경이 활성화된 상태에서 아래 Uvicorn 명령어를 사용하여 개발 서버를 구동합니다.

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

* `--reload`: 소스 코드(`main.py`) 변경 시 서버를 자동으로 재시작합니다. (개발 환경 전용)
* `--host 0.0.0.0`: 로컬 호스트뿐만 아니라 같은 공유기(네트워크) 내의 ESP32-CAM 및 외부 기기 접근을 허용합니다.
* `--port 8000`: 기본 포트 번호를 8000번으로 지정합니다.

> **최초 실행 시 주의사항**: 서버가 처음 구동될 때 `Ultralytics` 라이브러리가 기본 객체 감지 모델인 `yolov8n.pt` 파일(약 6MB)을 인터넷에서 자동으로 다운로드합니다. 이 과정에서 최초 1회에 한해 약간의 시간이 소요될 수 있습니다.

---

## 🔌 API 명세 및 라우팅 구조

본 서버는 자동 생성되는 Swagger UI를 지원합니다. 서버를 구동한 후 브라우저에서 `http://localhost:8000/docs` 또는 `http://localhost:8000/redoc`에 접속하면 시각화된 전체 API 명세 확인 및 테스트가 가능합니다.

![Backend Swagger UI Example](/docs/images/backend-swagger_ui.png)

### 1. 사용자 화면 및 정적 웹 서빙 (Frontend Router)

* **`GET /`**
* **설명**: 브라우저를 통해 루트 주소로 접속 시 메인 프론트엔드 대시보드 화면을 반환합니다.
* **반환**: `../frontend/index.html` 파일 (`FileResponse`)


* **`Static Routing`**
* 프론트엔드 코드 분리 및 모듈화 구조에 따라 백엔드에서 정적 자산 경로를 제공합니다.
* `/css` ➔ `../frontend/css` (디자인 테마 및 레이아웃 스타일)
* `/js` ➔ `../frontend/js` (스크립트 및 인터랙션 로직)
* `/data` ➔ `../frontend/data` (개발자 정보 등 정적 JSON 데이터 파일)

### 2. 하드웨어 및 테스트 API (Embedded/Hardware Router)

* **`POST /api/v2/device/upload`**
* **설명**: ESP32-CAM 기기가 촬영한 사진을 `multipart/form-data` 형식으로 수신합니다. 수신된 이미지는 `uploaded_images` 디렉토리에 타임스탬프 파일명으로 저장되며, 즉시 YOLOv8 모델을 통해 사람 객체(Class ID: 0) 감지 추론이 수행됩니다. 추론 결과는 전역 변수(`LATEST_COUNT`)에 실시간으로 업데이트됩니다.
* **인자**: `file: UploadFile` (바이너리 이미지 파일)
* **응답 예시**:
```json
{
  "status": "success",
  "message": "Image processed successfully",
  "file_path": "uploaded_images/20260520_202400.jpg",
  "detected_count": 3
}
```

* **`POST /api/v2/test/trigger`**
* **설명**: [Swagger UI 테스트용] 이 엔드포인트를 호출하면 수동 캡처 플래그가 활성화되어 차후 ESP32 기기가 폴링할 때 캡처 명령을 수신하도록 강제합니다.


* **`GET /api/v2/device/command`**
* **설명**: ESP32-CAM 임베디드 기기가 주기적으로 호출하는 명령 확인 통로입니다. 수동 캡처 플래그 상태에 따라 `capture` 또는 `idle` 명령을 응답합니다.



### 3. 클라이언트 웹 데이터 API (Client Data Router)

* **`GET /api/v2/count/current`**
* **설명**: 프론트엔드 웹 대시보드에서 5초 주기로 호출하는 실시간 인원수 조회 API입니다. 백엔드 메모리에 상주하고 있는 가장 최신의 감지 데이터(`LATEST_COUNT`)를 반환합니다.
* **응답 예시**: `{"count": 3}`


* **`GET /api/v2/stats/today`**
* **설명**: 오늘 당일의 시간대별(09시 ~ 현재 시간) 인원 변동 통계를 반환합니다.
* *비고*: 현재는 UI 차트 연동성 검증을 위해 `LATEST_COUNT` 기준의 더미 데이터를 리턴하는 구조이며, 차후 데이터베이스 연동 시 실제 내역 데이터 쿼리로 전환되어야 합니다.


* **`GET /api/v2/stats/weekly`**
* **설명**: 요일 대시보드 및 메인 통계 탭 차트 렌더링에 사용되는 최근 4주간의 시간대별 평균 인원 데이터를 반환합니다. (현재 가짜 데이터 서빙 중, 차후 DB 연동 필요)

---

## 📌 주요 코드 설명 및 확장 주의사항

### 1. CORS(Cross-Origin Resource Sharing) 설정

로컬 호스트 개발 및 타 도메인 배포 환경 간의 도메인 파편화로 인한 웹 브라우저 보안 제약을 방지하기 위해 `CORSMiddleware`가 기본 탑재되어 있습니다. 현재는 기기 및 브라우저 테스트 편의상 모든 출처(`allow_origins=["*"]`)를 허용하도록 되어 있으나, 향후 실제 도메인을 할당하여 외부 배포 운영 체계로 전환할 시에는 보안을 위해 실제 서비스 도메인 주소만 화이트리스트에 명시하는 것을 권장합니다.

### 2. 하드코딩 방지 및 상대 경로 참조 주의

백엔드 코드는 실행되는 터미널의 현재 작업 디렉토리(Current Working Directory) 위치를 기반으로 프론트엔드 폴더(`../frontend/`)를 역참조합니다. 따라서 반드시 `backend` 폴더 안으로 이동(`cd backend`)하신 후 서버 구동 명령을 수행하셔야 정적 자산 경로를 잃어버리는 404 에러를 방지할 수 있습니다.

### 3. 차후 확장 계획 (데이터베이스 레이어 구축)

현재 통계 데이터 조회 기능인 `/api/v2/stats/today` 및 `/api/v2/stats/weekly` 엔드포인트는 데이터베이스 연동 이전 단계이므로 고정된 상수 배열 및 임시 무작위 생성 로직을 포함하고 있습니다. 향후 시스템 신뢰도 고도화를 위해 PostgreSQL 또는 SQLite 등의 관계형 데이터베이스(RDBMS)를 도입하고, 이미지 업로드 추론 완료 시점(`upload_image`)마다 시간대별 인원 기록 로그를 테이블에 기록(Insert)한 후 통계 API 호출 시 집계 쿼리(Select)를 수행하도록 백엔드를 확장해야 합니다.