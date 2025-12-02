from flask import Flask, render_template, request, jsonify
import joblib
import re
import speech_recognition as sr
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

# --- CONFIGURATION ---
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

VECTORIZER_PATH = 'data/processed/tfidf_vectorizer.pkl'
MODEL_PATH = 'data/processed/language_model.pkl'

# --- LOAD MODELS ---
try:
    vectorizer = joblib.load(VECTORIZER_PATH)
    model = joblib.load(MODEL_PATH)
    print("✅ System Ready!")
except:
    print("❌ Error loading models.")
    vectorizer = None
    model = None

# --- CLEANING ---
def clean_text(text):
    if not isinstance(text, str): return ""
    text = text.lower() 
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    text = re.sub(r'[^\w\s]', '', text) 
    text = text.strip()
    return text

# --- PREDICTION HELPER ---
def get_prediction(text):
    cleaned = clean_text(text)
    vec = vectorizer.transform([cleaned])
    pred = model.predict(vec)[0]
    probs = model.predict_proba(vec)[0]
    conf = round(max(probs) * 100, 2)
    return pred, conf

# --- ROUTE 1: HOME ---
@app.route('/', methods=['GET', 'POST'])
def home():
    prediction = None
    confidence = None
    user_text = ""

    if request.method == 'POST':
        if 'text_input' in request.form:
            user_text = request.form['text_input']
            if user_text.strip():
                prediction, confidence = get_prediction(user_text)

    return render_template('index.html', 
                           prediction=prediction, 
                           confidence=confidence, 
                           user_text=user_text)

# --- ROUTE 2: LIVE MIC ---
# @app.route('/record', methods=['POST'])
# def record():
#     r = sr.Recognizer()
#     languages = ["en-US", "fr-FR", "ar-MA"]  # langues à tester
    
#     try:
#         with sr.Microphone() as source:
#             r.adjust_for_ambient_noise(source, duration=0.5)
#             audio = r.listen(source, timeout=5)

#         for lang in languages:
#             try:
#                 text = r.recognize_google(audio, language=lang)
#                 return jsonify({'status': 'success', 'text': text, 'detected_lang': lang})
#             except:
#                 continue
        
#         return jsonify({'status': 'error', 'message': 'Language not recognized'})
    
#     except Exception as e:
#         return jsonify({'status': 'error', 'message': str(e)})


# # --- ROUTE 3: FILE UPLOAD (FIXED) ---
# @app.route('/upload', methods=['POST'])
# def upload_file():
#     if 'audio_file' not in request.files:
#         return jsonify({'status': 'error', 'message': 'No audio file part'})
    
#     file = request.files['audio_file']
#     if file.filename == '':
#         return jsonify({'status': 'error', 'message': 'No selected file'})

#     if file:
#         filename = secure_filename(file.filename)
#         filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#         file.save(filepath)

#         r = sr.Recognizer()
#         try:
#             with sr.AudioFile(filepath) as source:
#                 audio_data = r.record(source)
#                 text = r.recognize_google(audio_data, language="ar-MA")
                
#                 # Predict immediately
#                 pred, conf = get_prediction(text)
                
#                 # RETURN JSON (Not HTML)
#                 return jsonify({
#                     'status': 'success', 
#                     'text': text,
#                     'prediction': pred,
#                     'confidence': conf
#                 })
#         except ValueError:
#             return jsonify({'status': 'error', 'message': 'Please upload a .WAV file'})
#         except Exception as e:
#             return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    app.run(debug=True)