import cv2
from threading import Thread

class CameraUSB:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.frame = None
        self.running = True
        Thread(target=self.update_frame, daemon=True).start()

    def update_frame(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                self.frame = frame

    def get_frame(self):
        if self.frame is None:
            return None
        _, jpeg = cv2.imencode('.jpg', self.frame)
        return jpeg.tobytes()

    def capture_frame(self):
        return self.frame if self.frame is not None else None

    def release(self):
        self.running = False
        self.cap.release()

# Instancia global
camera_usb = CameraUSB()