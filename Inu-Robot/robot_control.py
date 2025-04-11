import threading
import logging
import time
import json
from unitree_sdk2py.go2.sport.sport_client import SportClient
import cyclonedds
from cyclonedds.domain import DomainParticipant
from cyclonedds.sub import Subscriber
from cyclonedds.sub import DataReader
from cyclonedds.topic import Topic
from cyclonedds.pub import Publisher
from cyclonedds.pub import DataWriter
from unitree_sdk2py.idl.unitree_go.msg.dds_ import BmsState_
from ultrasonic import medir_distancia

logger = logging.getLogger(__name__)

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
        self.battery_percentage = None
        self.trajectory = []  
        self._start_bms_listener()

    def initialize(self):
        try:
            logger.info("Initializing robot control...")
            self.client = SportClient()
            self.client.SetTimeout(10.0)
            self.client.Init()
            self.running = True
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
            try:
                distancia = medir_distancia()
                if distancia and distancia < 45:
                    logger.warning(f"Obstáculo detectado a {distancia:.2f} cm. Deteniendo robot.")
                    self.stop_move()
                    time.sleep(1)
                    self.set_speeds(0, -0.3, 0.5)  # retrocede y gira
                    time.sleep(1.5)
                    self.stop_move()
                else:
                    with self.lock:
                        x_speed = self.x_speed
                        y_speed = self.y_speed
                        yaw_speed = self.yaw_speed
                    if y_speed != 0 or x_speed != 0 or yaw_speed != 0:
                        self.client.Move(y_speed, x_speed, yaw_speed)
                        self._record_step(x_speed, y_speed, yaw_speed)
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Error en _movement_loop: {e}")

    def set_speeds(self, x_speed, y_speed, yaw_speed):
        MAX_SPEED = 1.0
        x_speed = max(min(x_speed, MAX_SPEED), -MAX_SPEED)
        y_speed = max(min(y_speed, MAX_SPEED), -MAX_SPEED)
        yaw_speed = max(min(yaw_speed, MAX_SPEED), -MAX_SPEED)

        with self.lock:
            self.x_speed = x_speed
            self.y_speed = y_speed
            self.yaw_speed = yaw_speed

    def stand_up(self):
        self._reset_speeds()
        if self.client:
            self.client.StandUp()


    def stand_down(self):
        self._reset_speeds()
        if self.client:
            self.client.StandDown()


    def stop_move(self):
        self._reset_speeds()
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

    def sit(self):
        if self.client:
            self.client.Sit()
    
    def power_off(self):
        if self.client:
            logger.info("Powering off the robot...")
            self.client.PowerOff()

    def _start_bms_listener(self):
        def listen():
            while True:
                try:
                    participant = DomainParticipant()
                    subscriber = Subscriber(participant)
                    topic = Topic(participant, "BmsStateTopic", BmsState_)
                    reader = DataReader(subscriber, topic)

                    logger.info("Listening to BmsStateTopic...")
                    for sample in reader.take_iter():
                        if sample and sample.valid_data:
                            self.battery_percentage = sample.data.soc
                            logger.info(f"Battery updated: {self.battery_percentage}%")

                except Exception as e:
                        logger.error(f"Error in BMS listener: {e}")
                        time.sleep(5)
        thread = threading.Thread(target=listen, daemon=True)
        thread.start()



    def get_battery_status(self):
        """Return the latest battery percentage."""
        logger.debug(f"Current battery_percentage: {self.battery_percentage}")
        return self.battery_percentage
    
    def _record_step(self, x_speed, y_speed, yaw_speed):
        step = {
            "x_speed": x_speed,
            "y_speed": y_speed,
            "yaw_speed": yaw_speed,
            "timestamp": time.time()
        }
        self.trajectory.append(step)
        logger.debug(f"Recorded step: {step}")

    def save_trajectory(self, filename="trajectory.json"):
        with open(filename, "w") as file:
            json.dump(self.trajectory, file)
        logger.info(f"Trajectory saved to {filename}")

    def load_trajectory(self, filename="trajectory.json"):
        try:
            with open(filename, "r") as file:
                self.trajectory = json.load(file)
            logger.info(f"Trajectory loaded from {filename}")
        except Exception as e:
            logger.error(f"Error loading trajectory: {e}")

    def follow_trajectory(self):
        if not self.trajectory:
            logger.warning("No trajectory to follow.")
            return

        for step in self.trajectory:
            self.set_speeds(step["x_speed"], step["y_speed"], step["yaw_speed"])
            time.sleep(0.02)  # Mantiene la sincronización de los pasos
    
        self.stop_move()  # Detiene el robot al final

    def _reset_speeds(self):
        with self.lock:
            self.x_speed = 0
            self.y_speed = 0
            self.yaw_speed = 0

