from flask import Flask, render_template, Response
import cv2

app = Flask(__name__)

# Inicia la cámara
cam = cv2.VideoCapture(0)

def gen_frames():
    while True:
        success, frame = cam.read()
        if not success:
            break
        else:
            # Codifica el frame en formato JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            
            # Devuelve un stream tipo multipart
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return '''
        <html>
            <head><title>Cámara en vivo</title></head>
            <body>
                <h1>Transmisión en vivo desde la Raspberry Pi</h1>
                <img src="/video_feed">
            </body>
        </html>
    '''

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)