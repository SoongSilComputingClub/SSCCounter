from picamera2 import Picamera2
import time

import cv2


class PiImageCreater:
    def __init__(self, ksize, cam):
        self.ksize = ksize
        self.cam = cam

    def blurImage(self, frame, x, y, w, h):
        roi = frame[y:y+h, x:x+w]
        roi = cv2.blur(roi, (self.ksize, self.ksize))
        frame[y:y+h, x:x+w] = roi

    def toggleBlur(self):
        self.blur_enabled = not self.blur_enabled

    def createImage(self):
        try:
            self.cam.capture_file("photo.jpg")
        except KeyboardInterrupt:
            print('Image creation interrupted')


if __name__ == "__main__":
    picam2 = Picamera2()
    picam2.start()
    image_creater = PiImageCreater(12, picam2)
    image_creater.createImage()
