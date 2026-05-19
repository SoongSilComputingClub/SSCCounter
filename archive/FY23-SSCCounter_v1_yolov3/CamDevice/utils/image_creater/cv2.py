import cv2


class CvImageCreater:
    def __init__(self, ksize=12):
        self.ksize = ksize
        self.blur_enabled = True

    def blurImage(self, frame, x, y, w, h):
        roi = frame[y:y+h, x:x+w]
        roi = cv2.blur(roi, (self.ksize, self.ksize))
        frame[y:y+h, x:x+w] = roi

    def toggleBlur(self):
        self.blur_enabled = not self.blur_enabled

    def createImage(self):
        cam = cv2.VideoCapture(0)

        if not cam.isOpened():
            print('No camera!')
            return

        try:
            ret, frame = cam.read()
            if not ret:
                print('No frame')
                return

            key = cv2.waitKey(1)
            print(key)
            print(self.blur_enabled)

            if key == -1 and self.blur_enabled:
                x, y, w, h = 450, 400, 80, 10
                for _ in range(8):
                    self.blurImage(frame, x, y, w, h)
                    x += 3
                    y += h
                self.blurImage(frame, 390, 460, 40, 20)

            fliped = cv2.flip(frame, -1)
            cv2.imwrite('photo.jpg', fliped)

        except KeyboardInterrupt:
            print('Image creation interrupted')

        finally:
            cam.release()


if __name__ == "__main__":
    image_creater = CvImageCreater()
    image_creater.createImage()
