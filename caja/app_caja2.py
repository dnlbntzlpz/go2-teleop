from flask import Flask, render_template, Response, jsonify
import cv2
import Adafruit_DHT
import threading
import time

# Inicializa Flask
app = Flask(__name__)

# Configura sensor DHT11
sensor = Adafruit_DHT.DHT11
dht_pin = 4

# Datos compartidos
dht_data = {"temperatura": 0.0, "humedad": 0.0}


# Captura de cámara
cam = cv2.VideoCapture(0)

# Función para leer el DHT11 en segundo plano
def leer_dht():
    while True:
        h, t = Adafruit_DHT.read_retry(sensor, dht_pin)
        if h is not None and t is not None:
            dht_data["temperatura"] = t
            dht_data["humedad"] = h
        time.sleep(2)

# Inicia hilo para lectura continua del DHT11
threading.Thread(target=leer_dht, daemon=True).start()

# Generador de frames para el streaming de video
def gen_frames():
    while True:
        success, frame = cam.read()
        if not success:
            break
        _, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

# Ruta principal
@app.route('/')
def index():
    return render_template('index.html')


# Ruta del video
@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Refrescar solo datos del DHT11 (AJAX)
@app.route('/dht')
def dht():
    return jsonify(dht_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)