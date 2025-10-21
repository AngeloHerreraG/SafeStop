import os
import json
from app import app

# Funcion para obtener todos los videos de la carpeta static/video
# Se guardar en un archivo JSON en formato de diccionario
def load_feed_data():
    # Leeremos el contenido de la carpeta static/video
    videos = os.listdir(app.config['UPLOAD_FOLDER'] + 'video/')
    videos = sorted(videos)  # Ordenamos los videos alfabéticamente

    # Luego crearemos el diccionario de videos
    feedData = {}
    for idx, video in enumerate(videos, start=1):
        feedData[idx] = {'name': video, 'frames': {}}
    
    # Y finalmente, vaciamos los archivos generados anteriormente
    files = os.listdir(os.path.join(app.config['UPLOAD_FOLDER'], 'img'))
    hardcoded_files = ["Calle.png", "calle.png", "feed.jpg", "semaforo_rojo.png", "semaforo_verde.png"]
    for file in files:
        if file not in hardcoded_files:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], 'img', file))
    
    # Guardamos el diccionario en un archivo JSON
    with open(os.path.join(app.config['UPLOAD_FOLDER'], 'data', 'feed.json'), 'w') as outfile:
        json.dump(feedData, outfile, indent=4)
        
# Funcion para obtener el feed de videos desde el archivo JSON
def get_feed_data():
    # Cargamos el feed desde el archivo JSON
    with open(os.path.join(app.config['UPLOAD_FOLDER'], 'data', 'feed.json'), 'r') as outfile:
        feedData = json.load(outfile)
    return feedData

# Funcion para guardar el nuevo feedData en el archivo JSON
def save_feed_data(feedData):
    # Guardamos el diccionario en un archivo JSON
    with open(os.path.join(app.config['UPLOAD_FOLDER'], 'data', 'feed.json'), 'w') as outfile:
        json.dump(feedData, outfile, indent=4)