import RPi.GPIO as GPIO
import time

# Configura los pines
TRIG = 23
ECHO = 24

GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

def medir_distancia():
    # Enviar pulso
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    # Esperar por la señal de respuesta
    while GPIO.input(ECHO) == 0:
        inicio = time.time()
    while GPIO.input(ECHO) == 1:
        fin = time.time()

    # Calcular duración
    duracion = fin - inicio
    distancia = (duracion * 34300) / 2  # cm

    return distancia

# Prueba rápida
if __name__ == "__main__":
    try:
        while True:
            dist = medir_distancia()
            print(f"Distancia: {dist:.2f} cm")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("Finalizando...")
        GPIO.cleanup()

#from gpiozero import DistanceSensor
#sensor = DistanceSensor(echo=24, trigger=23, max_distance=4, threshold_distance=0.03)

#while True:
    #if sensor.distance < 0.03:  # 3cm convertidos a metros
        #print("¡Obstáculo detectado!")
