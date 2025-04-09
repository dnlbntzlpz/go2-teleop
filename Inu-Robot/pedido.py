import RPi.GPIO as GPIO
import time

# Configura el modo de los pines
GPIO.setmode(GPIO.BCM)

TRIG = 25
ECHO = 8

GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

try:
    while True:
        # Disparo del pulso ultrasónico
        GPIO.output(TRIG, False)
        time.sleep(0.5)
        GPIO.output(TRIG, True)
        time.sleep(0.00001)
        GPIO.output(TRIG, False)

        # Espera la respuesta del ECHO
        while GPIO.input(ECHO) == 0:
            pulse_start = time.time()
        while GPIO.input(ECHO) == 1:
            pulse_end = time.time()

        pulse_duration = pulse_end - pulse_start
        distance = pulse_duration * 17150  # en cm
        distance = round(distance, 2)

        print(f"Distancia: {distance} cm")

        if distance > 3:
            print("Pedido recogido")

        time.sleep(1)

except KeyboardInterrupt:
    print("Programa detenido")

finally:
    GPIO.cleanup()