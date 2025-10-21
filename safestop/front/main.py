from flask import render_template, request, jsonify, Response
from app import app, IA_SERVER, IA_URL
import json, requests, os
from utils import *

# Al cargar la pagina cargamos todo
print("Se ha iniciado el servidor Front de Safestop")
# Al cargar la aplicación, se cargan los videos
load_feed_data()

@app.route("/safestop/front/", methods=['GET'])
def index():
    feedData = get_feed_data()
    return render_template("Index.html", feedData=feedData)


# Tendremos una ruta para reiniciar el feedData, desde una petición POST
@app.route("/safestop/front/api/reset-data", methods=['GET', 'POST'])
def reset_data():
    # Si es una petición GET, devolvemos el formulario de reinicio
    if request.method == 'GET':
        feedData = get_feed_data()
        return render_template("Index.html", feedData=feedData, reset=True)
        
    # Si es una petición POST, reiniciamos el feedData
    # Tomamos la contraseña del body de la request
    try:
        data = request.get_json(force=True)
        password = data.get('password', None).strip().lower()
        
        if password != "safestop2025reset":
            return jsonify({'success': False, 'error': 'Contraseña incorrecta'}), 403

        load_feed_data()
        return jsonify({'success': True,}), 200
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# Cargamos el feed sin procesar ni hacer llamada al modelo
@app.route("/safestop/front/feed<int:num>", methods=['GET'])
def feed(num):
    return render_template("feed.html", id=num)


# Modificamos la ruta para que devuelva el feed a medida que se va procesando 
# mediante generadores o yields
@app.route("/safestop/front/api/feed_stream<int:num>", methods=['GET'])
def api_feed_stream(num):
    num = str(num)
    # Se carga el feed desde el archivo JSON
    feedData = get_feed_data()
    
    if num not in feedData:
        def stream_error():
            print("El video no existe")
            yield json.dumps({"error": "El video no existe"}) + '\n'
            return
        return Response(stream_error(), content_type='application/json')

    if feedData[num]['frames']:
        def stream_data():
            try:
                print("El video ya ha sido procesado, devolviendo resultados")
                yield json.dumps({'video_info': feedData[num]['frames']['video_info']}) + '\n'
                for key, value in feedData[num]['frames'].items():
                    if key != 'video_info':
                        yield json.dumps(value) + '\n'
                        
            except Exception as e:
                print("Error al procesar el video:", e)
                yield json.dumps({'error': 'Error al obtener los datos del video de la base de datos: {}'.format(e)}) + '\n'
                return
        return Response(stream_data(), content_type='application/json')

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'video', feedData[num]['name'])
    
    def stream_results():
        try: 
            lines = []
            success = True
            with open(filepath, 'rb') as video:
                files = {'file': video}
                data = {'name': feedData[num]['name']}
                headers = {'Authorization': "Bearer R2J4cmEgZnJwZXJnYiBjZWJscnBnYiBWTg"}
                apicall = requests.post(IA_SERVER + IA_URL + "_stream", files=files, data=data, headers=headers, stream=True)
                
            if apicall.status_code != 200:
                yield json.dumps({"error": "Error de la APIcall: {}".format(apicall.content)}) + '\n'
                return
            
            for line in apicall.iter_lines(decode_unicode=True):
                if line:
                    yield line + '\n'
                    lines.append(line)
            
        except Exception as e:
            success = False
            yield json.dumps({'error': 'Error de una excepcion en front: {}'.format(e)}) + '\n'
            print("Error de una excepcion en front:", e)
            return
            
        # Tras mandar todas las lineas, guardamos el feedData actualizado
        if success:
            try:
                results = {}
                for line in lines:
                    item = json.loads(line)
                    if 'video_info' in item:
                        results['video_info'] = item['video_info']
                    else:
                        results[f'{item["track_id"]}'] = item
                feedData[num]['frames'] = results
                save_feed_data(feedData)            
                
            except Exception as e:
                yield json.dumps({'error': 'Error al guardar los resultados: {}'.format(e)}) + '\n'
                return
    
    return Response(stream_results(), content_type='application/json')
    
    
# Ahora tendremos una ruta para subir imagenes a static
@app.route("/safestop/front/upload-image", methods=['POST'])
def upload_image():
    # Primero verificamos que la request tenga el token de autenticación
    secret_code = request.headers.get('Authorization', '')
    code = secret_code.replace("Bearer ", "")
    if code != "R2J4cmEgZnJwZXJnYiBjZWJscnBnYiBWTg":
        return jsonify({'error': 'Token de autenticación inválido'}), 403
    
    # Si pasa la verificación, procedemos a guardar la imagen
    image = request.files['image']
    image_name = request.form['name']
    if not image:
        return jsonify({"error": "No file provided"}), 400
    
    # Guardamos la imagen en el directorio static
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'img', image_name)
    image.save(image_path)

    return Response(status=200)


# Y tendremos una ruta para revisar si la imagen existe
@app.route("/safestop/front/api/check-image", methods=['POST'])
def check_image():
    # No verificamos el token de autenticación, pues por front no deberiamos ponerlo ya que en js el codigo secreto es visible
    data = request.get_json(force=True)
    img_path = data.get('path', None)
    if not img_path:
        return jsonify({'error': 'No se ha proporcionado la ruta de la imagen', 'exists': False}), 400
    
    # Esto hara que la ruta sea segura y no se pueda acceder a archivos fuera del directorio de imágenes
    safe_path = os.path.normpath(os.path.join(app.config['UPLOAD_FOLDER'], 'img', img_path.lstrip('/\\')))
    if not safe_path.startswith(os.path.normpath(os.path.join(app.config['UPLOAD_FOLDER'], 'img'))):
        return jsonify({'error': 'Ruta de imagen no válida', 'exists': False}), 400
    
    exists = os.path.exists(safe_path) or os.path.isfile(safe_path)
    return jsonify({'exists': exists})


if __name__ == "__main__":
    app.run(port=9001)
