# -*- coding: utf-8 -*-
from flask import Flask

# Constantes para hacer la llamada a la IA con un request POST
IA_SERVER = 'http://localhost:9002'

IA_URL = '/safestop/ia/predict'
UPLOAD_FOLDER = 'static/'

app = Flask(__name__, static_url_path='/safestop/front/static')

app.secret_key = "secret key"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024 # 200MB limites
