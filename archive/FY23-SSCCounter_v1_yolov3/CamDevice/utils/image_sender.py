import requests
import time
from datetime import datetime

from utils.image_creater.cv2 import CvImageCreater
from utils.image_creater.pi import PiImageCreater


class ImageSender:
    def __init__(self, upload_url, upload_filename, camera_type):
        self.upload_url = upload_url
        self.upload_filename = upload_filename
        if camera_type == "cv":
            self.image_creater = CvImageCreater()
        else:
            self.image_creater = PiImageCreater()

    def send_img(self):
        try:
            # 이미지 파일을 열고 서버에 업로드
            with open(self.upload_filename, 'rb') as f:
                r = requests.post(self.upload_url, files={'file': f})
            return r
        except Exception as e:
            print(f"Error sending image: {e}")
            return None

    def toggle_blur(self):
        self.image_creater.toggleBlur()  # ImageCreater의 블러 토글 호출

    def run(self):
        print("ImageSender.py Activate")
        while True:
            try:
                # 이미지 생성
                self.image_creater.createImage()

                # 이미지 업로드 시도
                r = self.send_img()
                if r is not None:
                    print(datetime.now(), r.text)

                # 2초 대기
                time.sleep(2)
            except KeyboardInterrupt:
                print("ImageSender.py 종료")
                break
