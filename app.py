from flask import Flask, render_template, request, jsonify
import joblib
import re
import speech_recognition as sr
import os
from werkzeug.utils import secure_filename
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except:
    PYDUB_AVAILABLE = False
import io

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

# --- ROUTE 2: AUDIO UPLOAD (Handles both file upload and live recording) ---
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'audio_file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No audio file part'})
    
    file = request.files['audio_file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'})

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        print(f"\n{'='*60}")
        print(f"🎤 Received audio file: {filename}")
        print(f"📁 File size: {os.path.getsize(filepath)} bytes")
        print(f"📝 File extension: {os.path.splitext(filename)[1]}")
        
        # Convert to WAV with multiple strategies
        wav_filepath = filepath
        
        if not PYDUB_AVAILABLE:
            print(f"❌ pydub not available - speech recognition will likely fail")
            return jsonify({'status': 'error', 'message': 'Audio processing library not available. Please install pydub and FFmpeg.'})
        
        try:
            print(f"🔄 Loading audio with pydub...")
            
            # Try to load the audio file
            try:
                audio = AudioSegment.from_file(filepath)
            except Exception as load_error:
                print(f"❌ Failed to load audio file: {load_error}")
                # Try forcing format based on extension
                ext = os.path.splitext(filename)[1].lower().replace('.', '')
                if ext in ['webm', 'ogg', 'mp4', 'wav', 'mp3']:
                    print(f"🔄 Retrying with explicit format: {ext}")
                    audio = AudioSegment.from_file(filepath, format=ext)
                else:
                    raise load_error
            
            # Get audio info
            duration_sec = len(audio) / 1000.0
            print(f"📊 Original audio:")
            print(f"   - Duration: {duration_sec:.2f}s")
            print(f"   - Channels: {audio.channels}")
            print(f"   - Sample Rate: {audio.frame_rate}Hz")
            print(f"   - Sample Width: {audio.sample_width} bytes")
            print(f"   - dBFS (volume): {audio.dBFS:.1f}")
            
            # Check if audio is too short
            if len(audio) < 300:  # Less than 0.3 seconds
                return jsonify({'status': 'error', 'message': f'Audio too short ({duration_sec:.1f}s). Please record at least 1 second of clear speech.'})
            
            # Check if audio is silent
            if audio.dBFS < -60:
                return jsonify({'status': 'error', 'message': f'Audio is too quiet (volume: {audio.dBFS:.1f}dBFS). Please speak louder or check microphone.'})
            
            # AGGRESSIVE audio enhancement for speech recognition
            print(f"🔧 Enhancing audio for speech recognition...")
            
            # 1. Convert to mono
            if audio.channels > 1:
                audio = audio.set_channels(1)
                print(f"  ✓ Converted to mono")
            
            # 2. Increase volume if too quiet
            original_dbfs = audio.dBFS
            if audio.dBFS < -25:
                gain = -20 - audio.dBFS
                audio = audio.apply_gain(gain)
                print(f"  ✓ Increased volume by {gain:.1f}dB ({original_dbfs:.1f}dBFS → {audio.dBFS:.1f}dBFS)")
            
            # 3. Normalize
            audio = audio.normalize()
            print(f"  ✓ Normalized audio (peak at {audio.max_dBFS:.1f}dBFS)")
            
            # 4. Remove silence from beginning and end (more aggressive)
            original_len = len(audio)
            audio = audio.strip_silence(silence_thresh=-45, padding=300)
            if len(audio) < original_len:
                print(f"  ✓ Trimmed silence ({original_len/1000:.2f}s → {len(audio)/1000:.2f}s)")
            
            # 5. Apply high-pass filter to remove low-frequency noise
            audio = audio.high_pass_filter(200)
            print(f"  ✓ Applied high-pass filter (removed <200Hz noise)")
            
            # 6. Set optimal sample rate for speech recognition
            audio = audio.set_frame_rate(16000)
            audio = audio.set_sample_width(2)  # 16-bit
            print(f"  ✓ Set to 16kHz, 16-bit")
            
            # Export processed audio - KEEP FOR DEBUGGING
            import time
            timestamp = int(time.time())
            debug_filename = f'debug_audio_{timestamp}.wav'
            wav_filepath = os.path.join(app.config['UPLOAD_FOLDER'], debug_filename)
            
            audio.export(wav_filepath, format='wav', parameters=["-ac", "1", "-ar", "16000"])
            print(f"✅ Processed audio saved: {debug_filename}")
            print(f"   Final specs: {len(audio)/1000:.2f}s, mono, 16kHz, {audio.dBFS:.1f}dBFS")
            
            # Remove original file
            if filepath != wav_filepath:
                try:
                    os.remove(filepath)
                except:
                    pass
                    
        except Exception as e:
            print(f"💥 Audio processing FAILED: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'status': 'error', 'message': f'Audio processing failed: {str(e)}. Try uploading a WAV file instead.'})

        # ✅ Try recognition with multiple strategies
        # PRIORITIZE French first, then English, then Arabic variants
        languages = [
            ("fr-FR", "French"),
            ("en-US", "English"),
            ("ar-MA", "Arabic (Morocco)"),
            ("ar-SA", "Arabic (Standard)")
        ]
        results = []
        errors = []
        
        # Strategy 1: Without noise adjustment (for clean recordings)
        print(f"\n📍 STRATEGY 1: Direct recognition (no noise adjustment)")
        try:
            with sr.AudioFile(wav_filepath) as source:
                print(f"📊 Audio duration: {source.DURATION:.2f}s, Sample rate: {source.SAMPLE_RATE}Hz, Width: {source.SAMPLE_WIDTH}")
                
                r1 = sr.Recognizer()
                r1.energy_threshold = 50
                r1.dynamic_energy_threshold = False
                
                audio_data = r1.record(source)
                
                for lang_code, lang_name in languages:
                    try:
                        print(f"  🌐 Trying {lang_name}...")
                        text = r1.recognize_google(audio_data, language=lang_code)
                        if text and len(text.strip()) > 0:
                            print(f"  ✅ SUCCESS: '{text}'")
                            pred, conf = get_prediction(text)
                            results.append({
                                'text': text,
                                'prediction': pred,
                                'confidence': conf,
                                'detected_lang': lang_code,
                                'lang_name': lang_name,
                                'strategy': 'direct'
                            })
                    except sr.UnknownValueError:
                        print(f"  ❌ Could not understand")
                    except Exception as e:
                        print(f"  ❌ Error: {e}")
                        
        except Exception as e:
            print(f"❌ Strategy 1 failed: {e}")
        
        # Strategy 2: With aggressive noise adjustment (for noisy recordings)
        if not results:
            print(f"\n📍 STRATEGY 2: With noise adjustment")
            try:
                with sr.AudioFile(wav_filepath) as source:
                    r2 = sr.Recognizer()
                    r2.energy_threshold = 100
                    r2.dynamic_energy_threshold = True
                    r2.dynamic_energy_adjustment_damping = 0.15
                    r2.dynamic_energy_ratio = 1.5
                    
                    # Adjust for noise
                    r2.adjust_for_ambient_noise(source, duration=min(1.0, source.DURATION))
                    audio_data = r2.record(source)
                    
                    for lang_code, lang_name in languages:
                        try:
                            print(f"  🌐 Trying {lang_name}...")
                            text = r2.recognize_google(audio_data, language=lang_code)
                            if text and len(text.strip()) > 0:
                                print(f"  ✅ SUCCESS: '{text}'")
                                pred, conf = get_prediction(text)
                                results.append({
                                    'text': text,
                                    'prediction': pred,
                                    'confidence': conf,
                                    'detected_lang': lang_code,
                                    'lang_name': lang_name,
                                    'strategy': 'noise-adjusted'
                                })
                        except sr.UnknownValueError:
                            print(f"  ❌ Could not understand")
                        except Exception as e:
                            print(f"  ❌ Error: {e}")
                            
            except Exception as e:
                print(f"❌ Strategy 2 failed: {e}")
        
        # Strategy 3: Partial recognition (show_all=True)
        if not results:
            print(f"\n📍 STRATEGY 3: Detailed recognition with alternatives")
            try:
                with sr.AudioFile(wav_filepath) as source:
                    r3 = sr.Recognizer()
                    r3.energy_threshold = 300
                    audio_data = r3.record(source)
                    
                    for lang_code, lang_name in languages:
                        try:
                            print(f"  🌐 Trying {lang_name} with show_all...")
                            response = r3.recognize_google(audio_data, language=lang_code, show_all=True)
                            if response and 'alternative' in response:
                                for alt in response['alternative']:
                                    if 'transcript' in alt and alt['transcript']:
                                        text = alt['transcript']
                                        confidence_score = alt.get('confidence', 0.5) * 100
                                        print(f"  ✅ Found: '{text}' (API confidence: {confidence_score:.1f}%)")
                                        pred, conf = get_prediction(text)
                                        results.append({
                                            'text': text,
                                            'prediction': pred,
                                            'confidence': conf,
                                            'detected_lang': lang_code,
                                            'lang_name': lang_name,
                                            'strategy': 'detailed',
                                            'api_confidence': confidence_score
                                        })
                                        break
                        except sr.UnknownValueError:
                            print(f"  ❌ Could not understand")
                        except Exception as e:
                            print(f"  ❌ Error: {e}")
                            
            except Exception as e:
                print(f"❌ Strategy 3 failed: {e}")
        
        # Return best result - prioritize by model prediction matching API language
        if results:
            # Score each result based on:
            # 1. Model confidence (primary)
            # 2. Whether model prediction matches API detected language (bonus)
            def calculate_score(result):
                score = result['confidence']
                
                # Map model predictions to expected language codes
                pred_lang_map = {
                    'Français': ['fr-FR'],
                    'English': ['en-US'],
                    'Darija': ['ar-MA', 'ar-SA']
                }
                
                # Bonus if model prediction aligns with API detection
                expected_codes = pred_lang_map.get(result['prediction'], [])
                if result['detected_lang'] in expected_codes:
                    score += 10  # Alignment bonus
                
                return score
            
            # Sort by score
            sorted_results = sorted(results, key=calculate_score, reverse=True)
            
            # Print all results for debugging
            print(f"\n📊 ALL RECOGNITION RESULTS:")
            for i, r in enumerate(sorted_results, 1):
                alignment = "✓" if r['prediction'] in r['lang_name'] or r['lang_name'] in r['prediction'] else "✗"
                print(f"  {i}. '{r['text']}' | API: {r['lang_name']} | Model: {r['prediction']} | Conf: {r['confidence']}% | Align: {alignment}")
            
            best_result = sorted_results[0]
            
            # USE MODEL PREDICTION as the final language (not the API detection)
            # This fixes the issue where French is detected as Darija by Google's API
            final_prediction = best_result['prediction']
            final_confidence = best_result['confidence']
            final_text = best_result['text']
            
            print(f"\n🎯 FINAL RESULT:")
            print(f"   Text: '{final_text}'")
            print(f"   API detected as: {best_result['lang_name']}")
            print(f"   Model classified as: {final_prediction} ✓")
            print(f"   Confidence: {final_confidence}%")
            print(f"{'='*60}\n")
            
            # Clean up on success
            try:
                os.remove(wav_filepath)
            except:
                pass
            
            # Return the MODEL prediction (not the API detection)
            return jsonify({
                'status': 'success',
                'text': final_text,
                'prediction': final_prediction,  # Use model prediction
                'confidence': final_confidence,
                'detected_lang': best_result['detected_lang'],  # Keep for debugging
                'lang_name': best_result['lang_name']  # Keep for debugging
            })
        else:
            print(f"\n❌ ALL STRATEGIES FAILED")
            print(f"📁 Processed audio saved for debugging: {wav_filepath}")
            print(f"   You can test this file manually or listen to it to check quality.")
            print(f"{'='*60}\n")
            
            # Keep the WAV file for debugging - don't delete it
            return jsonify({
                'status': 'error', 
                'message': 'Could not recognize speech. Check server console for details. Tips: Record for 2-3 seconds, speak clearly and loudly.',
                'debug_info': f'Audio saved as {os.path.basename(wav_filepath)} for debugging',
                'debug_file': wav_filepath
            })

if __name__ == '__main__':
    app.run(debug=True)