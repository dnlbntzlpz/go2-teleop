import cv2
import numpy as np
import base64
import time
import logging
from ultralytics import YOLO
from unitree_sdk2py.go2.video.video_client import VideoClient
from threading import Thread
import queue
import threading

logger = logging.getLogger(__name__)

class RobotCameraConfig:
    def __init__(self, width=320, height=240):
        self.width = width
        self.height = height
        self.client = None
        self.running = False
        self.target_fps = 30  # Increased FPS
        self.frame_interval = 1.0 / self.target_fps
        self.jpeg_quality = 70  # Improved but not maximum quality
        self.skip_frames = 1  # Process all frames
        self.last_frame_time = 0
        self.frame_count = 0
        self.socketio = None
        self.model = YOLO("yolov8n.pt")
        
        # Frame buffer
        self.frame_queue = queue.Queue(maxsize=2)
        self.processed_queue = queue.Queue(maxsize=2)
        
        # Processing configuration
        self.detection_enabled = True
        self.processing_thread = None
        self.emission_thread = None

    def set_socketio(self, socketio):
        self.socketio = socketio

    def initialize(self):
        try:
            logger.info("Initializing robot camera...")
            self.client = VideoClient()
            self.client.SetTimeout(3.0)
            self.client.Init()

            code, _ = self.client.GetImageSample()
            if code != 0:
                logger.error(f"Failed to get image from robot camera. Error code: {code}")
                return False

            self.running = True
            
            # Start processing threads
            self.processing_thread = Thread(target=self._process_frames_thread, daemon=True)
            self.emission_thread = Thread(target=self._emit_frames_thread, daemon=True)
            self.processing_thread.start()
            self.emission_thread.start()
            
            return True
        except Exception as e:
            logger.error(f"Robot camera initialization error: {str(e)}")
            return False

    def _capture_frame(self):
        """Captures and preprocesses a frame"""
        code, data = self.client.GetImageSample()
        if code == 0:
            image_data = np.frombuffer(bytes(data), dtype=np.uint8)
            frame = cv2.imdecode(image_data, cv2.IMREAD_COLOR)
            frame = cv2.resize(frame, (self.width, self.height))
            return frame
        return None

    def _process_frames_thread(self):
        """Thread dedicated to frame processing"""
        while self.running:
            try:
                frame = self._capture_frame()
                if frame is not None:
                    if self.detection_enabled:
                        results = self.model.predict(frame, imgsz=640, conf=0.5)
                        processed_frame = results[0].plot()
                    else:
                        processed_frame = frame

                    # Optimize compression
                    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
                    _, buffer = cv2.imencode('.jpg', processed_frame, encode_param)
                    frame_data = base64.b64encode(buffer).decode('utf-8')

                    # Use queue with timeout to avoid blocking
                    try:
                        self.processed_queue.put(frame_data, timeout=0.1)
                    except queue.Full:
                        self.processed_queue.get_nowait()  # Remove old frame
                        self.processed_queue.put(frame_data)
            except Exception as e:
                logger.error(f"Frame processing error: {str(e)}")
                time.sleep(0.01)

    def _emit_frames_thread(self):
        """Thread dedicated to frame emission"""
        while self.running:
            try:
                frame_data = self.processed_queue.get(timeout=0.1)
                if self.socketio is not None:
                    self.socketio.emit('frame', {'data': frame_data})
                    
                    current_time = time.time()
                    self.frame_count += 1
                    if self.frame_count % self.target_fps == 0:
                        actual_fps = self.target_fps / (current_time - self.last_frame_time)
                        logger.debug(f"Streaming at {actual_fps:.1f} FPS")
                        self.frame_count = 0
                        self.last_frame_time = current_time
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Frame emission error: {str(e)}")
                time.sleep(0.01)

    def cleanup(self):
        """Cleanup resources safely"""
        self.running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=1.0)
        if self.emission_thread:
            self.emission_thread.join(timeout=1.0)
        self.client = None
        logger.info("Camera cleanup completed")

    def toggle_detection(self, enabled=True):
        """Enable/disable object detection"""
        self.detection_enabled = enabled

    def process_frames(self):
        """Compatibility method to start processing"""
        if not self.initialize():
            logger.error("Failed to initialize camera")
            return
        
        try:
            while self.running:
                time.sleep(0.1)  # Small pause to avoid CPU consumption
        except KeyboardInterrupt:
            logger.info("Camera processing stopped by user")
        finally:
            self.cleanup()

# Create a global camera_config instance
camera_config = RobotCameraConfig()

# Adjust parameters
camera_config.width = 640  # Higher resolution
camera_config.height = 480
camera_config.jpeg_quality = 80  # Higher quality
camera_config.target_fps = 25  # Lower but more stable FPS

# Option 1: Using initialize() directly
camera_config.initialize()

# Option 2: Using the process_frames method
thread = threading.Thread(target=camera_config.process_frames)
thread.start()