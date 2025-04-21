import cv2

# Abre la cámara (0 = primer dispositivo USB conectado)
cam = cv2.VideoCapture(0)

if not cam.isOpened():
    print("No se pudo acceder a la cámara.")
    exit()

print("Transmisión iniciada. Presiona 'q' para salir.")

while True:
    ret, frame = cam.read()
    if not ret:
        print("Error al capturar imagen.")
        break

    # Muestra el video en una ventana
    cv2.imshow("Transmisión USB en tiempo real", frame)

    # Presiona 'q' para salir
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Libera recursos
cam.release()
cv2.destroyAllWindows()