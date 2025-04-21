import Adafruit_DHT
import time

# Tipo de sensor y pin de datos
sensor = Adafruit_DHT.DHT11
pin = 4  # GPIO 26

print("Iniciando lectura del DHT11...")

while True:
    humedad, temperatura = Adafruit_DHT.read_retry(sensor, pin)

    if humedad is not None and temperatura is not None:
        print(f"Temperatura: {temperatura:.1f}°C  |  Humedad: {humedad:.1f}%")
    else:
        print("Error al leer el sensor. Intentando nuevamente...")

    time.sleep(2)  # Espera de 2 segundos entre lecturas