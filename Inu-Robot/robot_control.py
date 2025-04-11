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
        self.current_trajectory = None
        self.trajectory_index = 0
        self.is_executing_trajectory = False
        self.paused_trajectory = None
        self.obstacle_avoidance_active = False

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
                    if not self.obstacle_avoidance_active:
                        self._handle_obstacle()
                else:
                    if self.obstacle_avoidance_active:
                        self._resume_after_obstacle()

                    # Continuar con movimiento normal o trayectoria
                    if self.is_executing_trajectory and self.current_trajectory:
                        self._execute_trajectory_step()
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

    def _handle_obstacle(self):
        logger.warning(f"Obstáculo detectado. Iniciando evasión.")
        self.obstacle_avoidance_active = True
        
        # Guardar estado actual si estamos en una trayectoria
        if self.is_executing_trajectory:
            self.paused_trajectory = {
                'trajectory': self.current_trajectory,
                'index': self.trajectory_index,
                'remaining_time': self.current_trajectory[self.trajectory_index]['t'] - (time.time() - self.last_step_time)
            }
        
        # Realizar maniobra de evasión
        self.stop_move()
        time.sleep(0.5)
        self.set_speeds(0, -0.3, 0.5)  # retrocede y gira
        time.sleep(1.5)
        self.stop_move()
        time.sleep(0.5)

    def _resume_after_obstacle(self):
        logger.info("Obstáculo evitado. Reanudando operación normal.")
        self.obstacle_avoidance_active = False
        
        if self.paused_trajectory:
            # Reanudar trayectoria
            self.current_trajectory = self.paused_trajectory['trajectory']
            self.trajectory_index = self.paused_trajectory['index']
            self.is_executing_trajectory = True
            self.last_step_time = time.time() - (self.paused_trajectory['remaining_time'] if 'remaining_time' in self.paused_trajectory else 0)
            self.paused_trajectory = None
            logger.info(f"Reanudando trayectoria desde paso {self.trajectory_index}")

    def _execute_trajectory_step(self):
        current_time = time.time()
        if current_time - self.last_step_time >= self.current_trajectory[self.trajectory_index]['t'] / 1000.0:
            cmd = self.current_trajectory[self.trajectory_index]
            self.client.Move(cmd['y'], cmd['x'], cmd['yaw'])
            
            self.trajectory_index += 1
            self.last_step_time = current_time
            
            if self.trajectory_index >= len(self.current_trajectory):
                self.stop_move()
                self.is_executing_trajectory = False
                self.current_trajectory = None
                self.trajectory_index = 0
                logger.info("Trayectoria completada")

    def execute_trajectory(self, trajectory):
        if not trajectory or len(trajectory) == 0:
            return
        
        logger.info(f"Iniciando ejecución de trayectoria con {len(trajectory)} pasos")
        self.current_trajectory = trajectory
        self.trajectory_index = 0
        self.is_executing_trajectory = True
        self.last_step_time = time.time()            

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
    
    #def _record_step(self, x_speed, y_speed, yaw_speed):
        step = {
            "x_speed": x_speed,
            "y_speed": y_speed,
            "yaw_speed": yaw_speed,
            "timestamp": time.time()
        }
        self.trajectory.append(step)
        logger.debug(f"Recorded step: {step}")

    #def save_trajectory(self, filename="trajectory.json"):
        with open(filename, "w") as file:
            json.dump(self.trajectory, file)
        logger.info(f"Trajectory saved to {filename}")

    #def load_trajectory(self, filename="trajectory.json"):
        try:
            with open(filename, "r") as file:
                self.trajectory = json.load(file)
            logger.info(f"Trajectory loaded from {filename}")
        except Exception as e:
            logger.error(f"Error loading trajectory: {e}")

    #def follow_trajectory(self):
        if not self.trajectory:
            logger.warning("No trajectory to follow.")
            return

        for step in self.trajectory:
            self.set_speeds(step["x_speed"], step["y_speed"], step["yaw_speed"])
            time.sleep(0.02)  # Mantiene la sincronización de los pasos
    
        self.stop_move()  # Detiene el robot al final

    #def _reset_speeds(self):
        with self.lock:
            self.x_speed = 0
            self.y_speed = 0
            self.yaw_speed = 0

