from flask import Flask, Response, render_template
import cv2
import numpy as np
from ultralytics import YOLO
import pyttsx3
import threading

app = Flask(__name__)
model = YOLO("yolov8n.pt")  # Usa un modelo más pequeño si necesitas rendimiento

engine = pyttsx3.init()
engine.setProperty('rate', 150)
hablado_anterior = ""

def get_light_color(roi):
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    red_mask = cv2.inRange(hsv, (0,70,50), (10,255,255)) + cv2.inRange(hsv, (160,70,50), (180,255,255))
    yellow_mask = cv2.inRange(hsv, (15,70,50), (35,255,255))
    green_mask = cv2.inRange(hsv, (40,70,50), (90,255,255))

    height = roi.shape[0]
    red_area = cv2.countNonZero(red_mask[0:int(height/3), :])
    yellow_area = cv2.countNonZero(yellow_mask[int(height/3):int(2*height/3), :])
    green_area = cv2.countNonZero(green_mask[int(2*height/3):, :])

    if red_area > 50:
        return "ROJO"
    elif yellow_area > 50:
        return "AMARILLO"
    elif green_area > 50:
        return "VERDE"
    return "INDETERMINADO"

alerta_actual = "Buscando semáforo..."

def gen_frames():
    global alerta_actual
    cap = cv2.VideoCapture(0)
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame)
        annotated = frame.copy()
        alerta_actual = "Buscando semáforo..."

        for r in results:
            for box in r.boxes:
                cls = int(box.cls[0])
                if cls == 9:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    roi = frame[y1:y2, x1:x2]
                    color = get_light_color(roi)
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 255), 2)
                    cv2.putText(annotated, f"Semaforo: {color}", (x1, y1-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

                    # Alerta lógica
                    if color == "ROJO":
                        alerta_actual = "¡ALTO! Semáforo en rojo."
                    elif color == "AMARILLO":
                        alerta_actual = "Precaución. Luz amarilla."
                    elif color == "VERDE":
                        alerta_actual = "Adelante. Luz verde."
                    else:
                        alerta_actual = "Semáforo no claro."
                    
                    # Hablar alerta
                    hablar_alerta(alerta_actual)

        # Mostrar alerta en imagen
        cv2.putText(annotated, alerta_actual, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        _, buffer = cv2.imencode('.jpg', annotated)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

def hablar_alerta(texto):
    global hablado_anterior
    if texto != hablado_anterior:
        hablado_anterior = texto
        threading.Thread(target=lambda: engine.say(texto) or engine.runAndWait()).start()
        
@app.route('/alerta')
def alerta():
    global alerta_actual
    return alerta_actual

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)