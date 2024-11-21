import socket
import sys
import ast
import time
from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.go2.sport.sport_client import SportClient

def main():
    if len(sys.argv) < 2:
        print(f"Uso: python3 {sys.argv[0]} networkInterface")
        sys.exit(-1)

    NETWORK_INTERFACE = sys.argv[1]
    PORT = 65432  # Mismo puerto que el cliente

    ChannelFactoryInitialize(0, NETWORK_INTERFACE)
    sport_client = SportClient()
    sport_client.SetTimeout(10.0)
    sport_client.Init()

    HOST = ''  # Escuchar en todas las interfaces

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Servidor escuchando en el puerto {PORT}...")
        conn, addr = s.accept()
        with conn:
            print('Conectado por', addr)
            buffer = ''
            while True:
                data = conn.recv(1024).decode()
                if not data:
                    print("Cliente desconectado.")
                    break
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    try:
                        # Convertir cadena de texto a diccionario
                        message = ast.literal_eval(line)
                        x_speed = message['x_speed']
                        y_speed = message['y_speed']
                        yaw_speed = message['yaw_speed']
                        commands = message['commands']

                        # Ejecutar comandos
                        for command in commands:
                            if command == "StandUp":
                                sport_client.StandUp()
                                sport_client.BalanceStand()
                                print("StandUp command executed.")
                            elif command == "StandDown":
                                sport_client.StandDown()
                                print("StandDown command executed.")
                            elif command == "MoveForward":
                                sport_client.Move(0.2, 0, 0)
                                print("MoveForward command executed.")
                            elif command == "SwitchGait0":
                                sport_client.SwitchGait(0)
                                print("SwitchGait(0) command executed.")
                            elif command == "SwitchGait1":
                                sport_client.SwitchGait(1)
                                print("SwitchGait(1) command executed.")
                            elif command == "StopMove":
                                sport_client.StopMove()
                                print("StopMove command executed.")
                            elif command == "BalanceStand":
                                sport_client.BalanceStand()
                                print("BalanceStand command executed.")
                            elif command == "RecoveryStand":
                                sport_client.RecoveryStand()
                                print("RecoveryStand command executed.")

                        # Enviar comando de movimiento
                        if x_speed != 0 or y_speed != 0 or yaw_speed != 0:
                            sport_client.Move(y_speed, x_speed, yaw_speed)
                            #print(f"Move command sent: y_speed={y_speed}, x_speed={x_speed}, yaw_speed={yaw_speed}")

                    except Exception as e:
                        print(f"Error al procesar el mensaje: {e}")
                        continue

    print("Cerrando servidor.")

if __name__ == "__main__":
    main()
