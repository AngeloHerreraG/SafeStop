# -*- coding: utf-8 -*-
from flask import Flask
from ultralytics import YOLO
import easyocr
import torch
import os

IA_SERVER = 'http://gate.dcc.uchile.cl:8632'
# IA_SERVER = 'http://localhost:9001'

IA_URL = '/safestop/front/upload-image'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OCR_model_path = os.path.abspath(os.path.join(BASE_DIR, 'EasyOCR', 'model'))
OCR_user_path = os.path.abspath(os.path.join(BASE_DIR, 'EasyOCR', 'user_network'))

app = Flask(__name__)

app.secret_key = "secret key"
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024 # 200MB limites

model = YOLO('best_nano_medium.pt')
reader = easyocr.Reader(lang_list=['en'], 
                        gpu=True, 
                        model_storage_directory=OCR_model_path, 
                        user_network_directory=OCR_user_path, 
                        recog_network='custom_model', 
                        detector=False, 
                        recognizer=True
)
