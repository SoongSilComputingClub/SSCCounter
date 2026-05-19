from datetime import datetime
import time

from yolo import YoloDetector

if __name__ == "__main__":
    yolo_machine = YoloDetector(
        "./Yolo_Folder/yolov3.weights", "./Yolo_Folder/yolov3.cfg", "darknet")
    print("yolo ready")

    while True:
        try:
            standard_time, ncnt_people = yolo_machine.run_machine()
        except:
            print(
                f"시간: {datetime.now()}  >>>  SSCCount: Error!")
            time.sleep(1)