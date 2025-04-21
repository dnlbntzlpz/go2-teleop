import time
import board
import busio
import adafruit_stts22h
i2c = busio.I2C(board.SCL, board.SDA)
while not i2c.try_lock():
    pass
print("Iniciando sensor...")
try:
    sensor = adafruit_stts22h.STTS22(i2c)
    print("Sensor inicializado correctamente")
except Exception as e:
    print(f"Error al inicializar el sensor: {e}")
    exit()
sensor.low_power = False  # Modo normal
def read_stts22h():
    try:
        temperature = sensor.temperature
        return {'temperature': round(temperature, 2)}
    except Exception as e:
        print(f"Error al leer el sensor: {e}")
        return {'temperature': None}
print("Iniciando lectura...")
while True:
    data = read_stts22h()
    print(f"Temperatura: {data['temperature']} °C")
    time.sleep(2)