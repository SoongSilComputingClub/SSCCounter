#  -*- coding: utf-8 -*-
from fastapi import FastAPI, Request, File, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime
import time
import asyncio

from utils.count.yolo import YoloDetector


yolo_machine = YoloDetector(
    "./yolo_data/yolov3.weights", "./yolo_data/yolov3.cfg", "darknet")
print("yolo ready")

status = {"people_count": -1, "analysis_time": "init time"}

async def count():
    while True:
        try:
            standard_time, ncnt_people = yolo_machine.run_machine()
            status["people_count"], status["analysis_time"] = ncnt_people, standard_time
        except:
            print(
                f"시간: {datetime.now()}  >>>  SSCCount: Error!")
        # 2초마다 갱신
        await asyncio.sleep(2)

## Backend ##

app = FastAPI(docs_url=None, redoc_url=None)
#app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
async def start_polling():
    asyncio.create_task(count())


@app.get("/", response_class=HTMLResponse)
async def Page(request: Request):
    SSCCount, Standard_Time = status["people_count"], status["analysis_time"]
    current_time = str(datetime.now())[0:21]  # 필요한 부분 가공
    print("새로고침", current_time)
    if int(SSCCount) <= 6:
        countable = 1
    else:
        countable = 0

    # index.html에 변수 값 전달
    return templates.TemplateResponse("index(Ver_8).html", {"request": request, "People_Count": int(SSCCount), "Countable": countable, "last_time": current_time, "get_time": current_time, "Get_Time": Standard_Time})


@app.get("/contributor", response_class=HTMLResponse)
async def ContributorPage(request: Request):
    return templates.TemplateResponse("Contribute.html", {"request": request})


@app.get("/SSCCounter.json")
async def nCnt():
    SSCCount, Standard_Time = status["people_count"], status["analysis_time"]
    print(SSCCount)

    return {"people_count": SSCCount, "analysis_time": Standard_Time}


@app.post("/uploadfile")
async def create_upload_file(file: UploadFile = File(...)):
    contents = await file.read()

    with open("./temp/"+file.filename, "wb") as f:
        f.write(contents)

    return {"filename": file.filename}
