from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO
from models import db, User
import logging
import sys
from robot_control import RobotControl
from camera_stream import camera_config
import threading
from unitree_sdk2py.core.channel import ChannelFactoryInitialize

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

@socketio.on('control_command')
def handle_control_command(data):
    command = data.get('command')
    if command == 'move':
        y_speed = data.get('y_speed', 0)
        x_speed = data.get('x_speed', 0)
        yaw_speed = data.get('yaw_speed', 0)
        print(x_speed, y_speed, yaw_speed)
        robot_control.set_speeds(x_speed, y_speed, yaw_speed)
    else:
        # For other commands, reset speeds to zero
        robot_control.set_speeds(0, 0, 0)
        if command == 'stand_up':
            robot_control.stand_up()
            robot_control.balance_stand()
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
        ChannelFactoryInitialize(0, 'eth0')
        logger.info("ChannelFactory initialized successfully.")
    except Exception as e:
        logger.error(f"ChannelFactory initialization error: {str(e)}")
        sys.exit(1)

    # Initialize robot camera
    camera_config.set_socketio(socketio)  # Set the socketio instance
    if camera_config.initialize():
        # Start frame processing in a separate thread
        thread = threading.Thread(target=camera_config.process_frames)
        thread.daemon = True
        thread.start()
        logger.info("Camera streaming started successfully.")
    else:
        logger.error("Failed to initialize robot camera.")

    # Initialize robot control
    robot_control = RobotControl(network_interface='eth0')
    if robot_control.initialize():
        logger.info("Robot control initialized successfully.")
    else:
        logger.error("Failed to initialize robot control.")

    try:
        socketio.run(app, host='0.0.0.0', port=8066, allow_unsafe_werkzeug=True)
    finally:
        if camera_config:
            camera_config.cleanup()
        if robot_control:
            robot_control.cleanup()