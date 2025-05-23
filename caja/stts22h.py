import time
import board
import adafruit_stts22h
# Inicializar bus I2C
i2c = board.I2C()  # usa los pines SDA y SCL por defecto en Raspberry Pi
# Inicializar sensor STTS22H
sensor = adafruit_stts22h.STTS22(i2c)
# Opcional: configurar modo de operación (puede ser 'low', 'normal', 'high')
sensor.low_power = False  # False = modo normal
def read_stts22h():
    try:
        temperature = sensor.temperature
        return {'temperature': round(temperature, 2)}
    except Exception as e:
        print(f"Error al leer el sensor: {e}")
        return {'temperature': None}
# Ejemplo de uso en tiempo real
while True:
    data = read_stts22h()
    print(f"Temperatura: {data['temperature']} °C")
    time.sleep(2)