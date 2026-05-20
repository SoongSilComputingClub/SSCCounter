# SSCCounter v2.1 - Embedded (ESP32-CAM)

SSCC 동아리방 실시간 인원 카운팅 시스템의 하드웨어 펌웨어 디렉토리입니다.  
ESP-IDF 프레임워크를 기반으로 하며, AI-Thinker 사의 ESP32-CAM 모듈을 활용하여 실시간으로 이미지를 캡처하고 FastAPI 백엔드 서버로 전송합니다.

---

## 🛠️ 필수 프로그램 및 개발 환경 (Prerequisites)

본 프로젝트를 빌드하고 플래싱하려면 아래의 프로그램들이 로컬 환경에 설치되어 있어야 합니다.

1. **ESP-IDF SDK (v5.x 이상 권장)**
   * 코어 컴파일 및 빌드 도구 체인입니다. 설치 가이드에 따라 환경 변수 등록까지 완료해야 합니다.
2. **VS Code (Visual Studio Code)**
   * 에디터 환경으로 권장하며, **ESP-IDF Extension** 플러그인을 설치하면 컴파일 및 모니터링이 편리해집니다.
3. **USB to UART 드라이버 (CP2102 또는 CH340)**
   * ESP32-CAM 보드를 PC와 연결하고 펌웨어를 다운로드하기 위해 가상 COM 포트 드라이버가 필요합니다.

---

## 📂 디렉토리 구조 (Directory Structure)

유지보수와 인수인계의 편의성을 위해 하드웨어 제어부와 핵심 비즈니스 로직을 모듈화 했습니다.


```text
embedded/ssccam/
├── CMakeLists.txt          # 프로젝트 최상위 빌드 파일
├── sdkconfig               # menuconfig 설정 결과 파일 (Git Ignore 대상)
├── dependencies.lock       # 컴포넌트 매니저 의존성 잠금 파일 (Git 관리 대상)
└── main/
    ├── CMakeLists.txt      # 메인 소스 빌드 스크립트
    ├── Kconfig.projbuild   # 전용 menuconfig 메뉴 템플릿
    ├── main.c              # 메인 루프 및 비즈니스 로직
    ├── wifi_manager.c/.h   # Wi-Fi 커넥션 및 재시도 이벤트 관리
    └── camera_manager.c/.h # AI-Thinker 핀맵 및 카메라 설정
```

---

## ⚙️ 프로젝트 설정 (idf.py menuconfig)

빌드하기 전, 필수적인 하드웨어 및 네트워크 설정을 위해 두 가지 세팅을 반드시 수행해야 합니다.

### 1. 외부 메모리(PSRAM) 활성화 (필수)

ESP32-CAM의 고해상도 이미지 버퍼를 안정적으로 확보하기 위해 외부 SPI RAM 설정을 변경해야 합니다.

1. 터미널에서 `idf.py menuconfig` 명령어를 실행합니다.
2. `Component config` ➔ `ESP PSRAM` 메뉴로 이동합니다.
3. `Support for external, SPI-connected RAM` 항목을 체크(`[*]`)하여 활성화합니다.
4. `SPI RAM config` ➔ `SPI RAM access method` 메뉴로 들어가 **`Make RAM allocatable using heap_caps_malloc(..., MALLOC_CAP_SPIRAM)`** 항목을 선택합니다.
* *이 설정을 생략하거나 다르게 지정하면 `frame buffer malloc failed` 에러가 발생하며 시스템이 멈춥니다.*

![Menuconfig SPI RAM config Setup Example-1](/docs/images/embedded-menuconfig_SPI_RAM_config_1.jpg)
![Menuconfig SPI RAM config Setup Example-2](/docs/images/embedded-menuconfig_SPI_RAM_config_2.jpg)

### 2. Wi-Fi 및 백엔드 URL 설정

우리 프로젝트 고유의 환경 변수를 설정하는 단계입니다.

1. `idf.py menuconfig` 메인 화면에서 **`SSCCounter Configuration`** 메뉴로 진입합니다.  
2. 아래 항목들을 본인의 환경에 맞게 입력합니다:
* **WiFi SSID**: 동아리방 혹은 테스트 환경의 Wi-Fi 이름
* **WiFi Password**: Wi-Fi 비밀번호
* **Backend Server URL (Upload)**: FastAPI 서버의 이미지 업로드 API 주소 (예: `http://192.168.0.7:8000/api/v2/device/upload`)
* **Backend Server URL (Command)**: FastAPI 서버의 명령 확인용 API 주소 (예: `http://192.168.0.7:8000/api/v2/device/command`)

![Menuconfig SSCCounter Configuration Setup Example](/docs/images/embedded-menuconfig_ssccounter_configuration.jpg)

---

## 🚀 실행 및 빌드 방법 (How to Build & Run)

모든 설정이 완료되었다면 아래 명령어를 순서대로 실행하여 기기에 펌웨어를 업로드하고 모니터링을 시작합니다.

### 1. Kconfig 템플릿 복사

최초 빌드 시, 예제 템플릿을 복사하여 환경 설정을 바인딩합니다.

```bash
cp main/Kconfig.projbuild.example main/Kconfig.projbuild
```

### 2. 타겟 디바이스 설정

```bash
idf.py set-target esp32
```

### 3. 컴파일, 플래싱 및 시리얼 모니터링 실행

보드가 PC에 연결된 상태(업로드 모드 점퍼 또는 버튼 조작 필요)에서 아래 통합 명령어를 실행합니다.

```bash
idf.py build flash monitor
```

### 4. 정상 작동 로그 확인

정상적으로 통신이 연결되면 시리얼 모니터에 아래와 같은 로그가 영어로 출력됩니다.

```text
I (1991) WiFi_Mgr: Got IP: 192.168.0.9
I (2031) Camera_Mgr: Detected OV2640 camera
I (2150) SSCCam_Main: System ready. Starting 30-second interval capture.
I (2160) SSCCam_Main: Capturing image...
I (2180) SSCCam_Main: Sending image to server...
I (2450) SSCCam_Main: HTTP Status Code: 200
```

---

## ⚠️ 주의 사항 및 트러블슈팅

* **Camera Init Failed (0xffffffff) 에러 발생 시**
  * 보드에 부착된 카메라 리본 케이블이 제대로 밀착되어 결합했는지 확인하세요.
  * `menuconfig`에서 PSRAM 설정이 제대로 적용되었는지 다시 검토하세요.


* **select() timeout / Connection failed 에러 발생 시**
  * PC와 ESP32-CAM이 같은 Wi-Fi 공유기(AP)에 연결되어 있는지 확인하세요.
  * 컴퓨터의 방화벽 설정으로 인해 8000번 포트 접근이 차단되었는지 확인하세요.
  * API 경로가 올바른지 확인하세요.  
