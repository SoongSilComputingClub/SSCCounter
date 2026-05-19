import cv2
import numpy as np
from datetime import datetime


class YoloDetector:
    def __init__(self, weights_path, cfg_path, framework):
        # YOLO 네트워크 불러오기
        self.net = cv2.dnn.readNet(weights_path, cfg_path, framework)
        self.layer_names = self.net.getLayerNames()
        self.output_layers = [self.layer_names[i - 1]
                              for i in self.net.getUnconnectedOutLayers()]

    def detect_objects(self, frame, size, score_threshold, nms_threshold):
        # 사물 class
        classes = ["person"]
        # 이미지의 높이, 너비, 채널 받아오기
        height, width, channels = frame.shape
        # 네트워크에 넣기 위한 전처리
        blob = cv2.dnn.blobFromImage(
            frame, 0.00392, (size, size), (0, 0, 0), True, crop=False)
        # 전처리된 blob 네트워크에 입력, readNet으로 만든 객체에 .setInput 함수로 적용
        self.net.setInput(blob)
        # 결과 받아오기
        outs = self.net.forward(self.output_layers)

        # 결과 데이터를 저장할 리스트들
        class_ids = []
        confidences = []
        boxes = []

        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                if confidence > 0.1:  # 신뢰도가 0.1보다 큰 경우에만 객체를 탐지로 인정
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)

                    w = int(detection[2] * width)
                    h = int(detection[3] * height)

                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)

                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)

        # Non-Maximum Suppression (NMS)를 사용하여 중복된 탐지 박스를 제거
        indexes = cv2.dnn.NMSBoxes(
            boxes, confidences, score_threshold=score_threshold, nms_threshold=nms_threshold)

        ncnt_people = 0

        for i in range(len(boxes)):
            if i in indexes:
                x, y, w, h = boxes[i]
                class_name = "person"
                label = f"{class_name} {confidences[i]:.2f}"
                color = (0, 255, 0)
                try:
                    class_name = classes[class_ids[i]]
                    if class_name == "person":
                        ncnt_people += 1  # 사람이 인식되면 ncnt_people 변수 +1
                        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                        cv2.rectangle(
                            frame, (x-1, y), (x + len(class_name) * 13 + 65, y - 25), color, -1)
                        cv2.putText(frame, label, (x, y - 8),
                                    cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (0, 0, 0), 2)
                except IndexError:
                    pass
                cv2.imwrite('./temp/analysis.jpg', frame)  # 이미지 저장

        return ncnt_people

    def run_machine(self):
        current_time = str(datetime.now())  # 현재시간 측정
        standard_time = current_time[11:19]  # 기준 시간 설정 (시, 분)

        img = "./temp/photo.jpg"  # 이미지 경로
        frame = cv2.imread(img)  # 이미지 읽어오기

        # 입력 사이즈 리스트 (Yolov3에서 사용되는 네트워크 입력 이미지 사이즈)
        size_list = [320, 416, 608]
        ncnt_people = self.detect_objects(
            frame=frame, size=size_list[2], score_threshold=0.4, nms_threshold=0.4)  # 이미지 분석
        
        print("시간: {0}  >>>  SSCCount: {1} 명".format(datetime.now(), ncnt_people))
        
        return standard_time, ncnt_people