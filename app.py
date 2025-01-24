import cv2
import numpy as np
from flask import Flask, render_template, request, jsonify, Response
from ultralytics import YOLO
from tracker import Tracker
from multiprocessing import Process, Queue

app = Flask(__name__)
model = YOLO('yolov5su.pt')
frame_queue = Queue()

detection_lines = []  # Armazena as linhas de detecção desenhadas pelo usuário
person_count_up = 0
person_count_down = 0
total_person_count = 0
video_source = 0  # Fonte de vídeo padrão (câmera principal)

def processed_frame_generator(queue):
    while True:
        frame = queue.get()
        if frame is None:
            break
        ret, jpeg = cv2.imencode('.jpg', frame)
        if not ret:
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')

def process_video(queue):
    cap = cv2.VideoCapture(0)  # Abre a câmera padrão
    with open("coco.txt", "r") as f:
        class_list = f.read().splitlines()

    tracker = Tracker()
    cy1, cy2 = 150, 200  # Coordenadas das linhas de detecção
    people_count_up, people_count_down = 0, 0
    id_last_positions = {}
    line1_touched, line2_touched = False, False  # Estado das linhas

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.resize(frame, (640, 360))

        # Predição com YOLO
        results = model.predict(frame)
        detections = results[0].boxes.data.cpu().numpy() if results[0].boxes.data is not None else []

        list_bbox = []
        for detection in detections:
            x1, y1, x2, y2, _, class_id = detection
            # Filtrar apenas pessoas
            if class_list[int(class_id)] == 'person':
                list_bbox.append([int(x1), int(y1), int(x2), int(y2)])

        # Atualizar o tracker
        bbox_id = tracker.update(list_bbox)

        line1_touched, line2_touched = False, False  # Reinicia o estado das linhas

        for bbox in bbox_id:
            x1, y1, x2, y2, obj_id = bbox
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

            # Desenhar o triângulo de detecção no centro do objeto
            triangle_pts = [(cx, cy), (cx - 10, cy + 20), (cx + 10, cy + 20)]
            cv2.polylines(frame, [np.array(triangle_pts, np.int32)], isClosed=True, color=(255, 0, 255), thickness=2)

            # Contagem de pessoas com base na direção
            if obj_id not in id_last_positions:
                id_last_positions[obj_id] = cy

            prev_cy = id_last_positions.get(obj_id)
            id_last_positions[obj_id] = cy

            # Verificar se prev_cy não é None antes de comparar
            if prev_cy is not None:
                if prev_cy < cy1 <= cy:  # Cruzou a linha de cima para baixo
                    people_count_down += 1
                    id_last_positions[obj_id] = None  # Evitar contagem duplicada
                elif prev_cy > cy2 >= cy:  # Cruzou a linha de baixo para cima
                    people_count_up += 1
                    id_last_positions[obj_id] = None  # Evitar contagem duplicada

            # Verificar se o triângulo de detecção toca as barras
            if cy1 - 5 <= cy <= cy1 + 5:
                line1_touched = True
            if cy2 - 5 <= cy <= cy2 + 5:
                line2_touched = True

            # Exibir bounding box e ID
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, str(obj_id), (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

        # Desenhar linhas de contagem com a cor baseada no estado
        color_line1 = (0, 0, 255) if line1_touched else (0, 255, 0)
        color_line2 = (0, 0, 255) if line2_touched else (0, 255, 0)
        cv2.line(frame, (0, cy1), (640, cy1), color_line1, 2)
        cv2.line(frame, (0, cy2), (640, cy2), color_line2, 2)

        # Contagem no frame
        cv2.putText(frame, f"Up: {people_count_up}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f"Down: {people_count_down}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # Adicionar frame à fila
        queue.put(frame)

    cap.release()
    queue.put(None)



@app.route('/set-video-source', methods=['POST'])
def set_video_source():
    global video_source
    video_source = request.json.get('source', 0)  # Define a nova fonte de vídeo
    return jsonify(status="Video source updated successfully")

@app.route('/set-lines', methods=['POST'])
def set_lines():
    global detection_lines
    detection_lines = [(tuple(line[0]), tuple(line[1]), line[2]) for line in request.json.get('lines', [])]
    return jsonify(status="Lines set successfully")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start-analysis', methods=['POST'])
def start_analysis():
    if frame_queue.empty():
        Process(target=process_video, args=(frame_queue,)).start()
        return jsonify(status="Processing started")
    return jsonify(status="Already running")

@app.route('/video_feed')
def video_feed():
    return Response(processed_frame_generator(frame_queue), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
