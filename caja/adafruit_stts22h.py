# Módulo Adafruit STTS22 simulado (fragmento adaptado para ejemplo educativo)
# Basado en: https://github.com/adafruit/Adafruit_CircuitPython_STTS22
import time
class STTS22:
    def __init__(self, i2c):
        self._i2c = i2c
        self._temp = 24.5  # valor fijo simulado
    @property
    def temperature(self):
        # Simula lectura
        return self._temp
    @property
    def low_power(self):
        return False
    @low_power.setter
    def low_power(self, val):
        pass