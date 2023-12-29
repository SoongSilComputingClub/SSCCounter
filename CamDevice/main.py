from utils.image_sender import ImageSender

if __name__ == "__main__":
    # 클래스 인스턴스 생성 및 실행
    upload_url = 'http://localhost:3000/uploadfile'
    upload_filename = 'photo.jpg'
    image_sender = ImageSender(upload_url, upload_filename, "cv")
    image_sender.run()
