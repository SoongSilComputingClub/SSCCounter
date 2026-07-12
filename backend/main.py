from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from database import close_database_pool, open_database_pool
from routers.device import router as device_router
from routers.public import router as public_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    open_database_pool()

    try:
        yield
    finally:
        close_database_pool()


app = FastAPI(title="SSCCounter API", version="2.1", lifespan=lifespan)

app.mount("/data", StaticFiles(directory="../frontend/data"), name="data")
app.mount("/css", StaticFiles(directory="../frontend/css"), name="css")
app.mount("/js", StaticFiles(directory="../frontend/js"), name="js")

# ---------------------------------------------
app.add_middleware(
    CORSMiddleware,
    # 개발 단계에서는 모든 도메인을 허용합니다.
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(public_router)
app.include_router(device_router)

# ---------------------------------------------


@app.get("/")
async def root():
    """
    브라우저로 서버 주소에 접속하면 index.html 웹페이지를 띄워줍니다.
    """
    return FileResponse("../frontend/index.html")
