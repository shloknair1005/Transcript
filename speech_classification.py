"""
Speech Quest - Flask Web Application
Run with: python app.py
"""

from flask import Flask, render_template, request, jsonify, session
import os
import json
import librosa
import numpy as np
import requests
from datetime import datetime
import tempfile
from werkzeug.utils import secure_filename
import warnings
from dotenv import load_dotenv
warnings.filterwarnings('ignore')

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = 'speech_quest_secret_key_2024'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Load Groq API key from environment
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# Check if API key is loaded
if not GROQ_API_KEY:
    print("=" * 60)
    print("⚠️  WARNING: GROQ_API_KEY not found in environment variables!")
    print("=" * 60)
    print("💡 Please create a .env file in the same directory as app.py")
    print("💡 Add this line to the .env file:")
    print("   GROQ_API_KEY=your_actual_api_key_here")
    print("=" * 60)
else:
    print("=" * 60)
    print("✅ Groq API key loaded successfully!")
    print(f"✅ API Key: {GROQ_API_KEY[:10]}...{GROQ_API_KEY[-4:]}")
    print("=" * 60)

# Create uploads folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ==================== CELEBRITY PROFILES ====================

CELEBRITY_PROFILES = {
    ('male', 'young'): ['Varun Dhawan', 'Ranbir Kapoor', 'Kartik Aaryan'],
    ('male', 'middle'): ['Shah Rukh Khan', 'Ranveer Singh', 'Hrithik Roshan'],
    ('male', 'senior'): ['Amitabh Bachchan', 'Naseeruddin Shah', 'Anupam Kher'],
    ('female', 'young'): ['Alia Bhatt', 'Janhvi Kapoor', 'Sara Ali Khan'],
    ('female', 'middle'): ['Deepika Padukone', 'Priyanka Chopra', 'Kareena Kapoor'],
    ('female', 'senior'): ['Jaya Bachchan', 'Waheeda Rehman', 'Shabana Azmi'],
}

ACHIEVEMENTS = [
    {"name": "First Words", "desc": "Record your first transcription", "xp": 50, "icon": "🎤"},
    {"name": "Chatterbox", "desc": "Speak 100 words", "xp": 100, "icon": "💬"},
    {"name": "Speaker Pro", "desc": "Speak 500 words", "xp": 250, "icon": "🗣️"},
    {"name": "Voice Master", "desc": "Speak 1000 words", "xp": 500, "icon": "🎙️"},
    {"name": "Quality First", "desc": "Achieve 8+ audio quality", "xp": 150, "icon": "⭐"},
    {"name": "Perfectionist", "desc": "Get 5 high-quality recordings", "xp": 300, "icon": "💎"},
    {"name": "Deep Voice", "desc": "Get Bass score 8+", "xp": 100, "icon": "🔊"},
    {"name": "Crystal Clear", "desc": "Get Clarity 8+", "xp": 100, "icon": "✨"},
    {"name": "Celebrity Match", "desc": "Get 90%+ celebrity match", "xp": 200, "icon": "🌟"},
    {"name": "Streak Master", "desc": "5 day streak", "xp": 250, "icon": "🔥"},
    {"name": "Gender Expert", "desc": "95%+ gender confidence", "xp": 150, "icon": "🎯"},
    {"name": "Smooth Operator", "desc": "Smoothness 8+", "xp": 100, "icon": "🌊"},
    {"name": "Power Voice", "desc": "Power score 8+", "xp": 100, "icon": "⚡"},
    {"name": "Rich Tone", "desc": "Richness 8+", "xp": 100, "icon": "🎨"},
    {"name": "Speech Master", "desc": "Unlock all achievements", "xp": 1000, "icon": "👑"},
]

# ==================== AUDIO PROCESSING ====================

def convert_audio_if_needed(audio_path):
    try:
        y, sr = librosa.load(audio_path, sr=None)
        return audio_path, False
    except:
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(audio_path)
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, "converted_audio.wav")
            audio.export(temp_path, format="wav", parameters=["-ac", "1", "-ar", "22050"])
            return temp_path, True
        except Exception as e:
            raise Exception(f"Error converting audio: {str(e)}")

def extract_audio_features(audio_path):
    working_path, _ = convert_audio_if_needed(audio_path)
    y, sr = librosa.load(working_path, sr=None)
    features = {}

    # Pitch
    pitches, magnitudes = librosa.piptrack(y=y, sr=sr, fmin=50, fmax=400)
    pitch_values = []
    for t in range(pitches.shape[1]):
        index = magnitudes[:, t].argmax()
        pitch = pitches[index, t]
        if pitch > 0:
            pitch_values.append(pitch)

    try:
        f0 = librosa.yin(y, fmin=50, fmax=400, sr=sr)
        f0_values = f0[f0 > 0]
        if len(f0_values) > 0:
            combined_pitch = np.concatenate([pitch_values, f0_values, f0_values]) if len(pitch_values) > 0 else f0_values
        else:
            combined_pitch = pitch_values if len(pitch_values) > 0 else [150]
    except:
        combined_pitch = pitch_values if len(pitch_values) > 0 else [150]

    if len(combined_pitch) > 0:
        q1, q3 = np.percentile(combined_pitch, [25, 75])
        iqr = q3 - q1
        filtered_pitch = [p for p in combined_pitch if q1-1.5*iqr <= p <= q3+1.5*iqr]

        if len(filtered_pitch) > 0:
            features.update({
                'pitch_mean': float(np.mean(filtered_pitch)),
                'pitch_median': float(np.median(filtered_pitch)),
                'pitch_std': float(np.std(filtered_pitch)),
                'pitch_range': float(np.max(filtered_pitch) - np.min(filtered_pitch))
            })
        else:
            features.update({'pitch_mean': 150.0, 'pitch_median': 150.0, 'pitch_std': 30.0, 'pitch_range': 100.0})

    # Formants
    spec = np.abs(librosa.stft(y))
    freqs = librosa.fft_frequencies(sr=sr)
    spectral_peaks = []
    for frame in spec.T[:100]:
        peaks = np.argsort(frame)[-5:]
        spectral_peaks.extend(freqs[peaks])

    if len(spectral_peaks) > 0:
        f1_candidates = [f for f in spectral_peaks if 200 < f < 1200]
        features['formant_f1_mean'] = float(np.mean(f1_candidates)) if len(f1_candidates) > 0 else 500.0
        f2_candidates = [f for f in spectral_peaks if 800 < f < 3500]
        features['formant_f2_mean'] = float(np.mean(f2_candidates)) if len(f2_candidates) > 0 else 1500.0
    else:
        features['formant_f1_mean'] = 500.0
        features['formant_f2_mean'] = 1500.0

    # Other features
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    for i in range(13):
        features[f'mfcc_{i+1}_mean'] = float(np.mean(mfccs[i]))

    features['spectral_centroid_mean'] = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)[0]))
    features['spectral_flatness_mean'] = float(np.mean(librosa.feature.spectral_flatness(y=y)[0]))
    features['zcr_mean'] = float(np.mean(librosa.feature.zero_crossing_rate(y)[0]))

    rms = librosa.feature.rms(y=y)[0]
    features['rms_mean'] = float(np.mean(rms))

    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    features['tempo'] = float(tempo)

    y_harmonic, y_percussive = librosa.effects.hpss(y)
    features['harmonic_mean'] = float(np.mean(np.abs(y_harmonic)))
    features['percussive_mean'] = float(np.mean(np.abs(y_percussive)))
    features['harmonic_to_percussive_ratio'] = float(features['harmonic_mean'] / (features['percussive_mean'] + 1e-6))
    features['duration'] = float(librosa.get_duration(y=y, sr=sr))

    return features

def estimate_gender_age(features):
    gender_score = 0
    effective_pitch = features['pitch_median']

    if effective_pitch < 140:
        gender_score -= 4
    elif effective_pitch < 155:
        gender_score -= 2
    elif effective_pitch < 175:
        gender_score += 0
    elif effective_pitch < 200:
        gender_score += 2
    else:
        gender_score += 4

    f1, f2 = features['formant_f1_mean'], features['formant_f2_mean']
    if f1 < 520 and f2 < 1400:
        gender_score -= 3
    elif f1 > 620 and f2 > 1700:
        gender_score += 3

    if features['spectral_centroid_mean'] < 1500:
        gender_score -= 1.5
    elif features['spectral_centroid_mean'] > 2500:
        gender_score += 1.5

    if gender_score < -1.5:
        gender = 'male'
        conf = float(min(95, 60 + abs(gender_score) * 8))
    elif gender_score > 1.5:
        gender = 'female'
        conf = float(min(95, 60 + abs(gender_score) * 8))
    else:
        gender = 'male' if effective_pitch < 165 else 'female'
        conf = 55.0

    age_score = 0
    if features['pitch_std'] < 15:
        age_score += 2
    if features['spectral_flatness_mean'] > 0.35:
        age_score += 2

    age_category = 'young' if age_score <= 0 else ('middle' if age_score <= 2 else 'senior')

    return gender, conf, age_category, 70.0

def calculate_voice_scores(features):
    scores = {}
    scores['bass'] = float(round(np.clip(10 - (features['pitch_mean'] - 80) / 20, 0, 10), 1))
    scores['treble'] = float(round(np.clip((features['spectral_centroid_mean'] - 1000) / 300, 0, 10), 1))
    scores['clarity'] = float(round(np.clip(features['zcr_mean'] * 100, 0, 10), 1))
    scores['smoothness'] = float(round(np.clip(10 - features['pitch_std'] / 10, 0, 10), 1))
    scores['power'] = float(round(np.clip(features['rms_mean'] * 100, 0, 10), 1))
    scores['warmth'] = float(round(scores['bass'] * 0.6 + scores['smoothness'] * 0.4, 1))
    scores['richness'] = float(round(np.clip(features['harmonic_to_percussive_ratio'] * 2, 0, 10), 1))
    scores['pitch_variation'] = float(round(np.clip(features['pitch_range'] / 50, 0, 10), 1))
    return scores

def get_celebrity_match(gender, age_category, voice_scores, features, api_key):
    possible_celebrities = CELEBRITY_PROFILES.get((gender, age_category), ['Unique Voice'])

    prompt = f"""Based on these voice characteristics, pick the BEST celebrity match:
Gender: {gender}, Age: {age_category}
Pitch: {features['pitch_mean']:.1f}Hz, Bass: {voice_scores['bass']}, Clarity: {voice_scores['clarity']}
Celebrities: {', '.join(possible_celebrities)}

Respond in JSON:
{{"celebrity_name": "name", "match_percentage": 75-95, "description": "sentence", "fun_fact": "fact", "standout_quality": "quality"}}"""

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": "Respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 500
            },
            timeout=30
        )

        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content'].strip()
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
            return json.loads(content.strip())
        return None
    except Exception as e:
        print(f"Error calling Groq API: {str(e)}")
        return None

# ==================== SESSION MANAGEMENT ====================

def init_session():
    if 'level' not in session:
        session['level'] = 1
        session['total_xp'] = 0
        session['xp_for_next_level'] = 100
        session['streak'] = 0
        session['words_spoken'] = 0
        session['unlocked_achievements'] = []
        session['high_quality_count'] = 0
        session['recordings_count'] = 0

# ==================== ROUTES ====================

@app.route('/')
def index():
    init_session()
    return render_template('index.html',
                         achievements=ACHIEVEMENTS,
                         session_data=session)

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        # Check if API key is configured
        if not GROQ_API_KEY:
            return jsonify({'error': 'Server API key not configured. Please check .env file.'}), 500

        # Check if file is present
        if 'audio_file' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400

        file = request.files['audio_file']

        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        print(f"📁 Received file: {file.filename}")

        # Save file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        print(f"💾 File saved to: {filepath}")
        print(f"🔄 Extracting audio features...")

        # Extract features
        features = extract_audio_features(filepath)
        print(f"✅ Features extracted!")

        gender, gender_conf, age_category, age_conf = estimate_gender_age(features)
        print(f"👤 Gender: {gender} ({gender_conf}%), Age: {age_category}")

        voice_scores = calculate_voice_scores(features)
        print(f"🎵 Voice scores calculated")

        print(f"🤖 Calling Groq API for celebrity match...")
        llm_result = get_celebrity_match(gender, age_category, voice_scores, features, GROQ_API_KEY)

        if llm_result:
            print(f"🌟 Celebrity match: {llm_result.get('celebrity_name', 'Unknown')}")
        else:
            print(f"⚠️  Could not get celebrity match from API")

        # Calculate audio quality
        quality_score = (voice_scores['clarity'] + voice_scores['smoothness'] +
                       voice_scores['power'] + voice_scores['richness']) / 4
        audio_quality = round(quality_score, 1)

        # Estimate words
        estimated_words = int(features['duration'] * 2.5)

        # Update session
        session['words_spoken'] = session.get('words_spoken', 0) + estimated_words
        session['recordings_count'] = session.get('recordings_count', 0) + 1

        if audio_quality >= 8:
            session['high_quality_count'] = session.get('high_quality_count', 0) + 1

        # Check achievements
        new_achievements = check_achievements(voice_scores, gender_conf, llm_result, audio_quality)

        # Clean up
        try:
            os.remove(filepath)
            print(f"🗑️  Cleaned up temporary file")
        except:
            pass

        result = {
            'celebrity_name': llm_result.get('celebrity_name', 'Unknown') if llm_result else 'Unknown',
            'match_percentage': llm_result.get('match_percentage', 85) if llm_result else 85,
            'description': llm_result.get('description', 'Unique voice') if llm_result else 'Unique voice',
            'fun_fact': llm_result.get('fun_fact', 'Your voice is special!') if llm_result else 'Your voice is special!',
            'standout_quality': llm_result.get('standout_quality', 'Authenticity') if llm_result else 'Authenticity',
            'gender': gender,
            'gender_confidence': round(gender_conf, 1),
            'age_category': age_category,
            'audio_quality': audio_quality,
            'estimated_words': estimated_words,
            'voice_scores': voice_scores,
            'features': {
                'pitch_mean': round(features['pitch_mean'], 1),
                'pitch_median': round(features['pitch_median'], 1),
                'pitch_range': round(features['pitch_range'], 1),
                'duration': round(features['duration'], 1)
            },
            'new_achievements': new_achievements,
            'session_data': {
                'level': session.get('level', 1),
                'total_xp': session.get('total_xp', 0),
                'xp_for_next_level': session.get('xp_for_next_level', 100),
                'words_spoken': session.get('words_spoken', 0),
                'unlocked_achievements': session.get('unlocked_achievements', []),
                'achievements_count': len(session.get('unlocked_achievements', []))
            }
        }

        print(f"✅ Analysis complete! Sending results...")
        return jsonify(result)

    except Exception as e:
        print(f"❌ Error during analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

def check_achievements(voice_scores, gender_conf, llm_result, audio_quality):
    new_achievements = []
    unlocked = session.get('unlocked_achievements', [])

    # First Words
    if "First Words" not in unlocked:
        new_achievements.append("First Words")
        add_xp(50)

    # Word count achievements
    words = session.get('words_spoken', 0)
    if words >= 100 and "Chatterbox" not in unlocked:
        new_achievements.append("Chatterbox")
        add_xp(100)
    if words >= 500 and "Speaker Pro" not in unlocked:
        new_achievements.append("Speaker Pro")
        add_xp(250)
    if words >= 1000 and "Voice Master" not in unlocked:
        new_achievements.append("Voice Master")
        add_xp(500)

    # Quality achievements
    if audio_quality >= 8:
        if "Quality First" not in unlocked:
            new_achievements.append("Quality First")
            add_xp(150)
        if session.get('high_quality_count', 0) >= 5 and "Perfectionist" not in unlocked:
            new_achievements.append("Perfectionist")
            add_xp(300)

    # Voice score achievements
    if voice_scores['bass'] >= 8 and "Deep Voice" not in unlocked:
        new_achievements.append("Deep Voice")
        add_xp(100)
    if voice_scores['clarity'] >= 8 and "Crystal Clear" not in unlocked:
        new_achievements.append("Crystal Clear")
        add_xp(100)
    if voice_scores['smoothness'] >= 8 and "Smooth Operator" not in unlocked:
        new_achievements.append("Smooth Operator")
        add_xp(100)
    if voice_scores['power'] >= 8 and "Power Voice" not in unlocked:
        new_achievements.append("Power Voice")
        add_xp(100)
    if voice_scores['richness'] >= 8 and "Rich Tone" not in unlocked:
        new_achievements.append("Rich Tone")
        add_xp(100)

    # Celebrity match
    if llm_result and llm_result.get('match_percentage', 0) >= 90 and "Celebrity Match" not in unlocked:
        new_achievements.append("Celebrity Match")
        add_xp(200)

    # Gender confidence
    if gender_conf >= 95 and "Gender Expert" not in unlocked:
        new_achievements.append("Gender Expert")
        add_xp(150)

    # Update session
    for achievement in new_achievements:
        if achievement not in unlocked:
            unlocked.append(achievement)
    session['unlocked_achievements'] = unlocked

    # Check Speech Master
    if len(unlocked) == 14 and "Speech Master" not in unlocked:
        new_achievements.append("Speech Master")
        unlocked.append("Speech Master")
        session['unlocked_achievements'] = unlocked
        add_xp(1000)

    return new_achievements

def add_xp(amount):
    session['total_xp'] = session.get('total_xp', 0) + amount

    while session['total_xp'] >= session.get('xp_for_next_level', 100):
        session['total_xp'] -= session['xp_for_next_level']
        session['level'] = session.get('level', 1) + 1
        session['xp_for_next_level'] = int(session['xp_for_next_level'] * 1.5)

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🎮 Starting Speech Quest Server...")
    print("="*60)
    print("📍 Server will run on: http://localhost:5000")
    print("📝 Press Ctrl+C to stop the server")
    print("="*60 + "\n")
    app.run(debug=True, port=5000)