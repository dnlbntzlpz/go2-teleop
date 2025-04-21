# fan_control.py
import RPi.GPIO as GPIO

FAN_PIN = 27

GPIO.setmode(GPIO.BCM)
GPIO.setup(FAN_PIN, GPIO.OUT)
GPIO.output(FAN_PIN, GPIO.LOW)

def turn_fan_on():
    GPIO.output(FAN_PIN, GPIO.HIGH)

def turn_fan_off():
    GPIO.output(FAN_PIN, GPIO.LOW)

def cleanup():
    GPIO.cleanup()