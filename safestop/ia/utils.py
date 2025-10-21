# -*- coding: utf-8 -*-
from app import IA_URL, IA_SERVER
from datetime import datetime
import os
import re
from zoneinfo import ZoneInfo
import requests
import threading
import io

import cv2

from app import model, reader

ZONE = ZoneInfo("America/Santiago")
CONFIDENCE_THRESHOLD = 0.1
ASPECT_RATIO_RANGE = (2.0, 4.0)
TRACKER_CONFIG_PATH = 'custom_botsort.yaml'
P = 2

SEMAFORO_INTERVAL = 5

def upload_image_to_front(archivo, nombre):
    try:
        # La imagen es de tipo ndarray y la pasaremos a bytes
        success, buffer = cv2.imencode('.png', archivo)
        if not success:
            raise Exception("Error al codificar la imagen a PNG")

        file = io.BytesIO(buffer.tobytes())
        file.name = nombre 
        # Luego subimos la imagen al servidor
        files = {'image': file}
        data = {'name': nombre}
        headers = {'Authorization': "Bearer R2J4cmEgZnJwZXJnYiBjZWJscnBnYiBWTg"}
        request = requests.post(IA_SERVER + IA_URL, files=files, data=data, headers=headers)
        
        if request.status_code != 200:
            print(f"Error al subir la imagen: {request.status_code} - {request.text}")
            raise Exception(f"Error al subir la imagen: {request.status_code} - {request.text}")
        
    except Exception as e:
        print(f"[ERROR] Subida async fallida: {e}")
        
def platesOCR(img, id):
    # redimensionar la imagen
    scale_factor = 5
    img_resized = cv2.resize(img, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)

    # convertir imagen a escala de grises
    img_gray = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)

    # OCR
    results = reader.recognize(img_gray, adjust_contrast=0.0)

    if not results:
        return ('No text', 0)
    else:
        print(f"Resultados de OCR para id {id}:")
        print(results[0][1])
        return (results[0][1], results[0][2])

def es_patente_valida(patente):
    """Verifica si la patente cumple con los formatos permitidos: LLLLNN, LLNNNN o con espacios."""
    patente = patente.upper()
    formato1 = re.compile(r'^[A-Z]{4}[0-9]{2}$')  # LLLLNN
    formato2 = re.compile(r'^[A-Z]{2}[0-9]{4}$')  # LLNNNN
    formato3 = re.compile(r'^[A-Z]{2} [A-Z]{2} [0-9]{2}$')  # LL LL NN
    formato4 = re.compile(r'^[A-Z]{2} [0-9]{2} [0-9]{2}$')  # LL NN NN
    return formato1.match(patente) or formato2.match(patente) or formato3.match(patente) or formato4.match(patente)

def formatear_patente(patente):
    """Formatea la patente a un formato estándar sin espacios."""
    patente = patente.upper()
    return patente.upper().replace(" ", "")

def lector_patentes_stream(video_path, video_name, video_pth):
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print(f"Error: No se pudo abrir el archivo de video {video_path}")
        return

    timestamp = os.path.getctime(video_pth)
    creation_time = datetime.fromtimestamp(timestamp).strftime("%H:%M")
    date_created = datetime.fromtimestamp(timestamp).strftime("%d/%m/%Y")

    video = cv2.VideoCapture(video_pth)
    fps = round(video.get(cv2.CAP_PROP_FPS))
    video.release()
    
    # Apenas tenemos los datos importantes se los mandamos inmediatamente al front
    yield {
        "video_info": {
            "name": video_name,
            "creation_time": creation_time,
            "fps": fps,
            "semaforo_interval": SEMAFORO_INTERVAL
        }
    }

    active_tracks = {}  # track_id -> dict con best detection
    best_scores = {}    # track_id -> best score
    last_seen_frame = {}  # track_id -> último frame visto
    frame_count = 0
    snapshot_frame_count = 0
    semaforo = "Verde"

    FRAME_SKIP = 1
    while cap.isOpened():
        for _ in range(FRAME_SKIP):
            ret, frame = cap.read()
            if not ret:
                break
            frame_count += 1
            if abs(frame_count - snapshot_frame_count) >= SEMAFORO_INTERVAL * fps:
                semaforo = "Rojo" if semaforo == "Verde" else "Verde"
                snapshot_frame_count = frame_count
                print(f"Semáforo cambiado a {semaforo} en el frame {frame_count}")

        if not ret:
            break

        if frame_count % 10 == 0:
            print(f"Procesando frame {frame_count}")

        try:
            results = model.track(source=frame,
                                conf=CONFIDENCE_THRESHOLD,
                                save=False,
                                verbose=False,
                                imgsz=640,
                                tracker=TRACKER_CONFIG_PATH,
                                persist=True,
                                stream=False)
        except Exception as e:
            print(f"Error al procesar el frame {frame_count}: {e}")
            continue

        boxes = results[0].boxes
        if hasattr(boxes, 'id') and boxes.id is not None:
            ids = boxes.id.int()
            confs = boxes.conf
            xyxy = boxes.xyxy

            for i in range(len(ids)):
                track_id = int(ids[i].item())
                conf = float(confs[i].item())
                bbox = xyxy[i].tolist()
                x1, y1, x2, y2 = map(int, bbox)
                width = x2 - x1
                height = y2 - y1
                aspect_ratio = width / height
                area = width * height

                if not (ASPECT_RATIO_RANGE[0] <= aspect_ratio <= ASPECT_RATIO_RANGE[1]):
                    continue

                score = area * (conf ** P)

                if track_id not in best_scores or score > best_scores[track_id]:
                    plate_crop = frame[y1:y2, x1:x2]
                    date = date_created

                    best_scores[track_id] = score
                    active_tracks[track_id] = {
                        'score': score,
                        'date': date,
                        'frame_count': frame_count,
                        'plate_crop': plate_crop,
                        'frame': frame,
                        'semaforo': semaforo
                    }

                last_seen_frame[track_id] = frame_count

        # Ahora verificamos si hay tracks que no hemos visto hace >= fps frames
        finished_tracks = []
        for track_id, last_seen in last_seen_frame.items():
            if abs(frame_count - last_seen) >= fps:
                finished_tracks.append(track_id)

        for track_id in finished_tracks:
            detection = active_tracks.pop(track_id, None)
            if detection:
                plate_crop = detection['plate_crop']
                frame_img = detection['frame']

                patent, _ = platesOCR(plate_crop, track_id)
                if es_patente_valida(patent):
                    plate_crop_path = f"{video_name}_plate_{track_id}.png"
                    frame_path = f"{video_name}_frame_{track_id}.png"

                    threading.Thread(target=upload_image_to_front, args=(plate_crop, f"{video_name}_plate_{track_id}.png")).start()
                    threading.Thread(target=upload_image_to_front, args=(frame_img, f"{video_name}_frame_{track_id}.png")).start()

                    yield {
                        "date": detection["date"],
                        "frame_count": detection["frame_count"],
                        "patent": formatear_patente(patent),
                        "semaforo": detection["semaforo"],
                        "plate_crop": plate_crop_path,
                        "frame": frame_path,
                        "track_id": track_id
                    }
            # Limpiar datos
            best_scores.pop(track_id, None)
            last_seen_frame.pop(track_id, None)

    cap.release()

    # Al final, cerrar cualquier track activo restante
    for track_id, detection in active_tracks.items():
        plate_crop = detection['plate_crop']
        frame_img = detection['frame']

        patent, _ = platesOCR(plate_crop, track_id)
        if es_patente_valida(patent):
            plate_crop_path = f"{video_name}_plate_{track_id}.png"
            frame_path = f"{video_name}_frame_{track_id}.png"

            threading.Thread(target=upload_image_to_front, args=(plate_crop, f"{video_name}_plate_{track_id}.png")).start()
            threading.Thread(target=upload_image_to_front, args=(frame_img, f"{video_name}_frame_{track_id}.png")).start()

            yield {
                "date": detection["date"],
                "time": detection["time"],
                "frame_count": detection["frame_count"],
                "patent": formatear_patente(patent),
                "semaforo": detection["semaforo"],
                "plate_crop": plate_crop_path,
                "frame": frame_path,
                "track_id": track_id
            }
    print("Procesamiento de video finalizado.")