from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO
from models import db, User
import cv2
import logging
import base64
import threading
import time
import numpy as np
import sys
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.video.video_client import VideoClient
from unitree_sdk2py.go2.sport.sport_client import SportClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

# Configuration
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class RobotCameraConfig:
    def __init__(self, width=320, height=240):  # Reduced resolution
        self.width = width
        self.height = height
        self.client = None
        self.running = False
        self.target_fps = 15  # Reduced FPS
        self.frame_interval = 1.0 / self.target_fps
        self.jpeg_quality = 50  # Reduced quality
        self.skip_frames = 2  # Process every nth frame
        self.last_frame_time = 0
        self.frame_count = 0

    def initialize(self):
        try:
            logger.info("Initializing robot camera...")
            #ChannelFactoryInitialize(0)
            self.client = VideoClient()
            self.client.SetTimeout(3.0)
            self.client.Init()

            code, _ = self.client.GetImageSample()
            if code != 0:
                logger.error(
                    f"Failed to get image from robot camera. Error code: {code}")
                return False

            self.running = True
            return True
        except Exception as e:
            logger.error(f"Robot camera initialization error: {str(e)}")
            return False

    def cleanup(self):
        self.running = False
        if self.client is not None:
            pass


class RobotControl:
    def __init__(self, network_interface='eth0'):
        self.network_interface = network_interface
        self.client = None
        self.running = False
        self.move_thread = None
        self.x_speed = 0
        self.y_speed = 0
        self.yaw_speed = 0
        self.lock = threading.Lock()

    def initialize(self):
        try:
            logger.info("Initializing robot control...")
            #ChannelFactoryInitialize(0, self.network_interface)
            self.client = SportClient()
            self.client.SetTimeout(10.0)
            self.client.Init()
            self.running = True
            # Start the movement thread
            self.move_thread = threading.Thread(target=self._movement_loop)
            self.move_thread.daemon = True
            self.move_thread.start()
            return True
        except Exception as e:
            logger.error(f"Robot control initialization error: {str(e)}")
            return False

    def cleanup(self):
        self.running = False
        if self.move_thread:
            self.move_thread.join()

    def _movement_loop(self):
        while self.running:
            with self.lock:
                x_speed = self.x_speed
                y_speed = self.y_speed
                yaw_speed = self.yaw_speed
            try:
                # Always send movement commands
                self.client.Move(y_speed, x_speed, yaw_speed)
            except Exception as e:
                logger.error(f"Error sending Move command: {e}")
            time.sleep(0.02)  # Sleep for 20ms

    def set_speeds(self, x_speed, y_speed, yaw_speed):
        with self.lock:
            self.x_speed = x_speed
            self.y_speed = y_speed
            self.yaw_speed = yaw_speed

    # Define methods to send commands to the robot
    def stand_up(self):
        with self.lock:
            self.x_speed = 0
            self.y_speed = 0
            self.yaw_speed = 0
        if self.client:
            self.client.StandUp()

    def stand_down(self):
        with self.lock:
            self.x_speed = 0
            self.y_speed = 0
            self.yaw_speed = 0
        if self.client:
            self.client.StandDown()

    def stop_move(self):
        with self.lock:
            self.x_speed = 0
            self.y_speed = 0
            self.yaw_speed = 0
        if self.client:
            self.client.StopMove()

    def balance_stand(self):
        if self.client:
            self.client.BalanceStand()

    def recovery_stand(self):
        if self.client:
            self.client.RecoveryStand()

    def switch_gait(self, gait_type):
        if self.client:
            self.client.SwitchGait(gait_type)


def process_frames():
    """Optimized frame capture and processing"""
    skip_count = 0

    while camera_config.running:
        current_time = time.time()
        elapsed = current_time - camera_config.last_frame_time

        # Skip frames if we're falling behind
        if elapsed < camera_config.frame_interval:
            time.sleep(0.001)  # Short sleep to prevent CPU hogging
            continue

        try:
            skip_count += 1
            if skip_count < camera_config.skip_frames:
                continue
            skip_count = 0

            # Get frame from robot camera
            code, data = camera_config.client.GetImageSample()

            if code == 0:
                # Convert to numpy array and decode
                image_data = np.frombuffer(bytes(data), dtype=np.uint8)
                frame = cv2.imdecode(image_data, cv2.IMREAD_COLOR)

                # Resize frame to reduce processing load
                frame = cv2.resize(
                    frame, (camera_config.width, camera_config.height))

                # Compress frame with lower quality
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY),
                                camera_config.jpeg_quality]
                _, buffer = cv2.imencode('.jpg', frame, encode_param)

                # Emit frame
                frame_data = base64.b64encode(buffer).decode('utf-8')
                socketio.emit('frame', {'data': frame_data})

                camera_config.frame_count += 1
                if camera_config.frame_count % camera_config.target_fps == 0:
                    actual_fps = camera_config.target_fps / \
                        (current_time - camera_config.last_frame_time)
                    logger.debug(f"Streaming at {actual_fps:.1f} FPS")
                    camera_config.frame_count = 0

                camera_config.last_frame_time = current_time
            else:
                logger.error(
                    f"Failed to get image from robot camera. Error code: {code}")
                time.sleep(0.1)

        except Exception as e:
            logger.error(f"Frame processing error: {str(e)}")
            time.sleep(0.1)


@socketio.on('control_command')
def handle_control_command(data):
    command = data.get('command')
    if command == 'move':
        y_speed = data.get('y_speed', 0)
        x_speed = data.get('x_speed', 0)
        yaw_speed = data.get('yaw_speed', 0)
        robot_control.set_speeds(x_speed, y_speed, yaw_speed)
    else:
        # For other commands, reset speeds to zero
        robot_control.set_speeds(0, 0, 0)
        if command == 'stand_up':
            robot_control.stand_up()
        elif command == 'stand_down':
            robot_control.stand_down()
        elif command == 'stop_move':
            robot_control.stop_move()
        elif command == 'balance_stand':
            robot_control.balance_stand()
        elif command == 'recovery_stand':
            robot_control.recovery_stand()
        elif command == 'switch_gait':
            gait_type = data.get('gait_type', 0)
            robot_control.switch_gait(gait_type)
        else:
            logger.warning(f"Unknown command received: {command}")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/control')
@login_required
def control():
    return render_template('control.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('control'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('control'))

        flash('Invalid username or password')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('control'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


def init_db():
    with app.app_context():
        db.create_all()


if __name__ == '__main__':
    init_db()

    try:
        # Reemplaza 'eth0' con tu interfaz de red si es necesario
        ChannelFactoryInitialize(0, 'eth0')
        logger.info("ChannelFactory initialized successfully.")
    except Exception as e:
        logger.error(f"ChannelFactory initialization error: {str(e)}")
        sys.exit(1)

    # Initialize robot camera
    camera_config = RobotCameraConfig()
    if camera_config.initialize():
        # Start frame processing in a separate thread
        thread = threading.Thread(target=process_frames)
        thread.daemon = True
        thread.start()
    else:
        logger.error("Failed to initialize robot camera.")

    # Initialize robot control
    robot_control = RobotControl(network_interface='eth0')  # Adjust network interface if needed
    if robot_control.initialize():
        logger.info("Robot control initialized successfully.")
    else:
        logger.error("Failed to initialize robot control.")

    try:
        socketio.run(app, host='0.0.0.0', port=5001, allow_unsafe_werkzeug=True)
    finally:
        if camera_config:
            camera_config.cleanup()
        if robot_control:
            robot_control.cleanup()
