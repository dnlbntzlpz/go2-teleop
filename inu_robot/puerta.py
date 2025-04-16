from gpiozero import Servo
from time import sleep

# Configura el pin GPIO donde está conectado el servo (ej. GPIO17)
servo = Servo(17)

# Mover el servo a 90 grados aprox.
servo.max()  # Posición máxima
sleep(1)     # Esperar para asegurar el movimiento

# Si deseas volver al centro o mínimo puedes usar:
# servo.mid()  # Centro (~0 grados)
# servo.min()  # Mínimo (~-90 grados)

servo.detach()  # Liberar el servo