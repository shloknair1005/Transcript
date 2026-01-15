"""
Speech Quest - Integrated with Voice Analysis & Celebrity Matching

Features:
- Direct WAV recording (no FFmpeg needed)
- Automatic voice analysis after recording
- Celebrity voice matching with AI
- Full gamification system
- Real-time transcription

Installation:
pip install flask flask-cors librosa numpy requests python-dotenv

Setup:
1. Create a .env file with: GROQ_API_KEY=your_key_here
2. Run: python app.py
"""

from flask import Flask, render_template_string, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
import base64
import wave
import librosa
import numpy as np
import requests
import tempfile
from dotenv import load_dotenv
import warnings
warnings.filterwarnings('ignore')

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)
app.secret_key = 'speech_quest_integrated_2024'

# Create directories
AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Audio')
REVIEW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Review')
GAME_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'GameData')

for directory in [AUDIO_DIR, REVIEW_DIR, GAME_DIR]:
    os.makedirs(directory, exist_ok=True)

# Load Groq API key
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

if not GROQ_API_KEY:
    print("\n" + "="*60)
    print("⚠️  WARNING: GROQ_API_KEY not found!")
    print("="*60)
    print("💡 Create a .env file with: GROQ_API_KEY=your_key_here")
    print("="*60 + "\n")
else:
    print("\n" + "="*60)
    print("✅ Groq API key loaded successfully!")
    print(f"✅ Key: {GROQ_API_KEY[:10]}...{GROQ_API_KEY[-4:]}")
    print("="*60 + "\n")

# Celebrity profiles
CELEBRITY_PROFILES = {
    ('male', 'young'): ['Varun Dhawan', 'Ranbir Kapoor', 'Kartik Aaryan', 'Vicky Kaushal', 'Sidharth Malhotra'],
    ('male', 'middle'): ['Shah Rukh Khan', 'Ranveer Singh', 'Hrithik Roshan', 'Saif Ali Khan', 'Akshay Kumar'],
    ('male', 'senior'): ['Amitabh Bachchan', 'Naseeruddin Shah', 'Anupam Kher', 'Paresh Rawal'],
    ('female', 'young'): ['Alia Bhatt', 'Janhvi Kapoor', 'Sara Ali Khan', 'Ananya Panday', 'Kiara Advani'],
    ('female', 'middle'): ['Deepika Padukone', 'Priyanka Chopra', 'Kareena Kapoor', 'Katrina Kaif', 'Vidya Balan'],
    ('female', 'senior'): ['Jaya Bachchan', 'Waheeda Rehman', 'Shabana Azmi', 'Rekha'],
}

# ==================== VOICE ANALYSIS FUNCTIONS ====================

def extract_audio_features(audio_path):
    """Extract comprehensive audio features for voice analysis"""
    y, sr = librosa.load(audio_path, sr=None)
    features = {}

    # Pitch extraction
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
            combined_pitch = np.concatenate([pitch_values, f0_values]) if len(pitch_values) > 0 else f0_values
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

    # MFCCs
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    for i in range(13):
        features[f'mfcc_{i+1}_mean'] = float(np.mean(mfccs[i]))

    # Spectral features
    features['spectral_centroid_mean'] = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)[0]))
    features['spectral_flatness_mean'] = float(np.mean(librosa.feature.spectral_flatness(y=y)[0]))
    features['zcr_mean'] = float(np.mean(librosa.feature.zero_crossing_rate(y)[0]))

    # Energy
    rms = librosa.feature.rms(y=y)[0]
    features['rms_mean'] = float(np.mean(rms))

    # Tempo
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    features['tempo'] = float(tempo)

    # Harmonic/percussive
    y_harmonic, y_percussive = librosa.effects.hpss(y)
    features['harmonic_mean'] = float(np.mean(np.abs(y_harmonic)))
    features['percussive_mean'] = float(np.mean(np.abs(y_percussive)))
    features['harmonic_to_percussive_ratio'] = float(features['harmonic_mean'] / (features['percussive_mean'] + 1e-6))
    features['duration'] = float(librosa.get_duration(y=y, sr=sr))

    return features

def estimate_gender_age(features):
    """Estimate gender and age from voice features"""
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
    """Calculate detailed voice quality scores"""
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
    """Get celebrity voice match using Groq API"""
    possible_celebrities = CELEBRITY_PROFILES.get((gender, age_category), ['Unique Voice'])

    prompt = f"""Based on these voice characteristics, pick the BEST celebrity match from Bollywood:
Gender: {gender}, Age: {age_category}
Pitch: {features['pitch_mean']:.1f}Hz, Bass: {voice_scores['bass']}, Clarity: {voice_scores['clarity']}
Warmth: {voice_scores['warmth']}, Richness: {voice_scores['richness']}
Possible matches: {', '.join(possible_celebrities)}

Respond with ONLY valid JSON (no markdown, no code blocks):
{{"celebrity_name": "name", "match_percentage": 75-95, "description": "one exciting sentence about voice similarity", "fun_fact": "interesting fact about the celebrity", "standout_quality": "what makes this voice special"}}"""

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": "You are a voice analysis expert. Respond with valid JSON only, no markdown formatting."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 500
            },
            timeout=30
        )

        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content'].strip()
            # Clean up markdown formatting if present
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
            content = content.strip()
            return json.loads(content)
        return None
    except Exception as e:
        print(f"❌ Groq API Error: {str(e)}")
        return None

# ==================== ROUTES ====================

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/save_audio', methods=['POST'])
def save_audio():
    """Save audio and perform voice analysis"""
    try:
        data = request.json
        audio_base64 = data.get('audio', '')
        transcript = data.get('transcript', '')
        quality = data.get('quality', 0)
        game_data = data.get('gameData', {})

        if ',' in audio_base64:
            audio_base64 = audio_base64.split(',')[1]

        audio_bytes = base64.b64decode(audio_base64)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recording_{timestamp}.wav"
        filepath = os.path.join(AUDIO_DIR, filename)

        # Save the WAV file
        with open(filepath, 'wb') as f:
            f.write(audio_bytes)

        print(f"\n{'='*60}")
        print(f"🎤 ANALYZING VOICE...")
        print(f"{'='*60}")
        print(f"📄 File: {filename}")

        # Perform voice analysis
        voice_analysis = None
        if GROQ_API_KEY:
            try:
                features = extract_audio_features(filepath)
                gender, gender_conf, age_category, age_conf = estimate_gender_age(features)
                voice_scores = calculate_voice_scores(features)

                print(f"👤 Gender: {gender} ({gender_conf:.1f}%)")
                print(f"📅 Age: {age_category}")
                print(f"🎵 Voice Scores: Bass={voice_scores['bass']}, Clarity={voice_scores['clarity']}")

                # Get celebrity match
                llm_result = get_celebrity_match(gender, age_category, voice_scores, features, GROQ_API_KEY)

                if llm_result:
                    print(f"🌟 Celebrity Match: {llm_result.get('celebrity_name', 'Unknown')} ({llm_result.get('match_percentage', 0)}%)")

                    voice_analysis = {
                        'celebrity_name': llm_result.get('celebrity_name', 'Unknown'),
                        'match_percentage': llm_result.get('match_percentage', 85),
                        'description': llm_result.get('description', 'Unique voice'),
                        'fun_fact': llm_result.get('fun_fact', 'Your voice is special!'),
                        'standout_quality': llm_result.get('standout_quality', 'Authenticity'),
                        'gender': gender,
                        'gender_confidence': round(gender_conf, 1),
                        'age_category': age_category,
                        'voice_scores': voice_scores,
                        'pitch_mean': round(features['pitch_mean'], 1),
                        'pitch_range': round(features['pitch_range'], 1)
                    }
                else:
                    print(f"⚠️  Could not get celebrity match")
                    voice_analysis = {
                        'celebrity_name': 'Analyzing...',
                        'match_percentage': 0,
                        'description': 'Voice analysis in progress',
                        'gender': gender,
                        'voice_scores': voice_scores
                    }
            except Exception as e:
                print(f"⚠️  Voice analysis error: {str(e)}")
                voice_analysis = None

        print(f"{'='*60}\n")

        # Save game data with voice analysis
        game_filename = f"game_state_{timestamp}.json"
        game_filepath = os.path.join(GAME_DIR, game_filename)

        with open(game_filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': timestamp,
                'transcript': transcript,
                'quality': float(quality),
                'audio_file': filename,
                'gameData': game_data,
                'word_count': len(transcript.split()),
                'voice_analysis': voice_analysis
            }, f, indent=4)

        return jsonify({
            'success': True,
            'filename': filename,
            'format': 'WAV (16-bit PCM, 44100 Hz, Mono)',
            'compatible': True,
            'gameData': game_data,
            'voice_analysis': voice_analysis
        })

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/submit_rating', methods=['POST'])
def submit_rating():
    try:
        data = request.json
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"review_{timestamp}.json"
        filepath = os.path.join(REVIEW_DIR, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

        print(f"📝 Review saved: {filepath}")
        return jsonify({'success': True, 'filename': filename})

    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Speech Quest - Voice Analysis</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container { max-width: 1400px; margin: 0 auto; }

        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }

        .header h1 {
            font-size: 2.8em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }

        .game-stats-bar {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }

        .stat-card {
            background: white;
            border-radius: 12px;
            padding: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            text-align: center;
        }

        .stat-label {
            font-size: 0.85em;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 5px;
        }

        .stat-value {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }

        .main-content {
            display: grid;
            grid-template-columns: 1fr 2fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }

        .card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }

        .card h2 {
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.5em;
        }

        button {
            width: 100%;
            padding: 12px;
            font-size: 1em;
            border-radius: 8px;
            border: none;
            cursor: pointer;
            font-weight: 600;
            background: #667eea;
            color: white;
            margin: 5px 0;
        }

        button:hover { background: #5568d3; }
        button:disabled { background: #ccc; cursor: not-allowed; }

        .recording-btn { background: #10b981; }
        .recording-btn:hover { background: #059669; }
        .recording-btn.recording {
            background: #ef4444;
            animation: pulse 1.5s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }

        .transcript-display {
            background: #f9fafb;
            border: 2px solid #e5e7eb;
            border-radius: 10px;
            padding: 20px;
            min-height: 200px;
            max-height: 400px;
            overflow-y: auto;
            font-size: 1.1em;
            line-height: 1.6;
        }

        /* Celebrity Match Modal */
        .celebrity-modal {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.9);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 3000;
            animation: fadeIn 0.3s;
        }

        .celebrity-modal.show { display: flex; }

        .celebrity-content {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 40px;
            border-radius: 20px;
            max-width: 600px;
            text-align: center;
            color: white;
            animation: slideUp 0.5s;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        @keyframes slideUp {
            from { transform: translateY(50px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }

        .celebrity-icon {
            font-size: 5em;
            margin-bottom: 20px;
            animation: bounce 1s;
        }

        @keyframes bounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-20px); }
        }

        .celebrity-name {
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 15px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }

        .match-percentage {
            font-size: 4em;
            font-weight: bold;
            margin: 20px 0;
            text-shadow: 3px 3px 6px rgba(0,0,0,0.3);
        }

        .celebrity-description {
            font-size: 1.2em;
            line-height: 1.6;
            margin: 20px 0;
            background: rgba(255,255,255,0.1);
            padding: 15px;
            border-radius: 10px;
        }

        .voice-details {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin: 25px 0;
        }

        .voice-detail {
            background: rgba(255,255,255,0.15);
            padding: 15px;
            border-radius: 10px;
            backdrop-filter: blur(10px);
        }

        .voice-detail-label {
            font-size: 0.9em;
            opacity: 0.9;
            margin-bottom: 5px;
        }

        .voice-detail-value {
            font-size: 1.5em;
            font-weight: bold;
        }

        .fun-fact {
            background: rgba(255,255,255,0.2);
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            font-style: italic;
        }

        .visualizer-bars {
            display: flex;
            align-items: flex-end;
            height: 60px;
            gap: 3px;
            justify-content: space-around;
            background: #1f2937;
            border-radius: 8px;
            padding: 10px;
            margin: 15px 0;
        }

        .bar {
            flex: 1;
            background: linear-gradient(to top, #667eea, #764ba2);
            border-radius: 3px 3px 0 0;
            transition: height 0.1s;
            min-height: 2px;
        }

        .xp-popup {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: linear-gradient(135deg, #8b5cf6, #ec4899);
            color: white;
            padding: 30px 50px;
            border-radius: 20px;
            font-size: 2em;
            font-weight: bold;
            box-shadow: 0 10px 40px rgba(139, 92, 246, 0.5);
            z-index: 1000;
            animation: xpBounce 0.6s;
            display: none;
        }

        .xp-popup.show { display: block; }

        @keyframes xpBounce {
            0%, 100% { transform: translate(-50%, -50%) scale(1); }
            50% { transform: translate(-50%, -50%) scale(1.2); }
        }

        @media (max-width: 1200px) {
            .main-content { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎮 Speech Quest + Voice Analysis</h1>
            <p>Record your voice and discover your celebrity match!</p>
        </div>

        <!-- Game Stats Bar -->
        <div class="game-stats-bar">
            <div class="stat-card">
                <div class="stat-label">Level</div>
                <div class="stat-value" id="playerLevel">1</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total XP</div>
                <div class="stat-value" id="totalXP">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Words Spoken</div>
                <div class="stat-value" id="totalWords">0</div>
            </div>
        </div>

        <!-- Main Content -->
        <div class="main-content">
            <!-- Left Panel: Controls -->
            <div class="card">
                <h2>🎯 Controls</h2>
                <button id="startBtn" class="recording-btn" onclick="startRecording()">
                    🎙️ Start Recording
                </button>
                <button id="stopBtn" onclick="stopRecording()" disabled>
                    ⏹️ Stop & Analyze
                </button>

                <div class="visualizer-bars" id="visualizer">
                    <div class="bar"></div>
                    <div class="bar"></div>
                    <div class="bar"></div>
                    <div class="bar"></div>
                    <div class="bar"></div>
                    <div class="bar"></div>
                    <div class="bar"></div>
                    <div class="bar"></div>
                    <div class="bar"></div>
                    <div class="bar"></div>
                </div>
            </div>

            <!-- Center Panel: Transcription -->
            <div class="card">
                <h2>💬 Live Transcription</h2>
                <div class="transcript-display" id="transcriptDisplay">
                    Click "Start Recording" to begin...
                </div>
            </div>

            <!-- Right Panel: Last Result -->
            <div class="card">
                <h2>🌟 Last Analysis</h2>
                <div id="lastResult" style="color: #6b7280; text-align: center;">
                    No analysis yet
                </div>
            </div>
        </div>
    </div>

    <!-- XP Popup -->
    <div class="xp-popup" id="xpPopup">
        +<span id="xpAmount">0</span> XP!
    </div>

    <!-- Celebrity Match Modal -->
    <div class="celebrity-modal" id="celebrityModal">
        <div class="celebrity-content">
            <div class="celebrity-icon">🌟</div>
            <div class="celebrity-name" id="celebName">Analyzing...</div>
            <div class="match-percentage" id="matchPercent">--%</div>
            
            <div class="voice-details">
                <div class="voice-detail">
                    <div class="voice-detail-label">Gender</div>
                    <div class="voice-detail-value" id="genderValue">-</div>
                </div>
                <div class="voice-detail">
                    <div class="voice-detail-label">Age Category</div>
                    <div class="voice-detail-value" id="ageValue">-</div>
                </div>
                <div class="voice-detail">
                    <div class="voice-detail-label">Bass</div>
                    <div class="voice-detail-value" id="bassValue">-</div>
                </div>
                <div class="voice-detail">
                    <div class="voice-detail-label">Clarity</div>
                    <div class="voice-detail-value" id="clarityValue">-</div>
                </div>
            </div>

            <div class="celebrity-description" id="celebDescription">
                Your voice analysis will appear here...
            </div>

            <div class="fun-fact" id="funFact">
                💡 Fun Fact: Loading...
            </div>

            <button onclick="closeCelebrityModal()" style="background: rgba(255,255,255,0.2); margin-top: 20px;">
                Continue Quest
            </button>
        </div>
    </div>

    <script>
        let gameData = {
            level: 1,
            xp: 0,
            totalWords: 0,
            totalRecordings: 0
        };

        let recognition, audioContext, scriptProcessor, analyser, microphone;
        let audioChunks = [];
        let isRecording = false;
        let currentTranscript = '';
        let sampleRate = 44100;

        window.onload = () => {
            loadGameData();
            initSpeechRecognition();
            updateUI();
        };

        function loadGameData() {
            const saved = localStorage.getItem('speechQuestData');
            if (saved) {
                gameData = JSON.parse(saved);
            }
        }

        function saveGameData() {
            localStorage.setItem('speechQuestData', JSON.stringify(gameData));
        }

        function updateUI() {
            document.getElementById('playerLevel').textContent = gameData.level;
            document.getElementById('totalXP').textContent = gameData.xp;
            document.getElementById('totalWords').textContent = gameData.totalWords;
        }

        function gainXP(amount) {
            gameData.xp += amount;
            document.getElementById('xpAmount').textContent = amount;
            const popup = document.getElementById('xpPopup');
            popup.classList.add('show');
            setTimeout(() => popup.classList.remove('show'), 1500);

            if (gameData.xp >= gameData.level * 100) {
                gameData.level++;
            }

            updateUI();
            saveGameData();
        }

        function initSpeechRecognition() {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SpeechRecognition) {
                alert('Speech recognition not supported. Use Chrome, Edge, or Safari.');
                return;
            }

            recognition = new SpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = 'en-US';

            recognition.onresult = (event) => {
                let interimTranscript = '';

                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const transcript = event.results[i][0].transcript;

                    if (event.results[i].isFinal) {
                        currentTranscript += transcript + ' ';
                        const words = transcript.trim().split(/\s+/).length;
                        gameData.totalWords += words;
                        gainXP(words);
                        updateUI();
                    } else {
                        interimTranscript += transcript;
                    }
                }

                updateTranscriptDisplay(interimTranscript);
            };

            recognition.onend = () => {
                if (isRecording) {
                    recognition.start();
                }
            };
        }

        function updateTranscriptDisplay(interimText) {
            const display = document.getElementById('transcriptDisplay');
            let html = '';
            if (currentTranscript) {
                html += `<div>${currentTranscript}</div>`;
            }
            if (interimText) {
                html += `<div style="color: #667eea; font-weight: 500;">${interimText}</div>`;
            }
            display.innerHTML = html || '<div style="color: #9ca3af;">Listening... start speaking</div>';
            display.scrollTop = display.scrollHeight;
        }

        async function startRecording() {
            try {
                audioChunks = [];
                currentTranscript = '';

                const stream = await navigator.mediaDevices.getUserMedia({
                    audio: {
                        sampleRate: 44100,
                        channelCount: 1,
                        echoCancellation: true,
                        noiseSuppression: true,
                        autoGainControl: true
                    }
                });

                audioContext = new (window.AudioContext || window.webkitAudioContext)({
                    sampleRate: 44100
                });
                sampleRate = audioContext.sampleRate;

                analyser = audioContext.createAnalyser();
                analyser.fftSize = 2048;

                microphone = audioContext.createMediaStreamSource(stream);
                scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);

                microphone.connect(analyser);
                microphone.connect(scriptProcessor);
                scriptProcessor.connect(audioContext.destination);

                scriptProcessor.onaudioprocess = (e) => {
                    if (!isRecording) return;
                    
                    const inputData = e.inputBuffer.getChannelData(0);
                    const pcm16 = new Int16Array(inputData.length);
                    
                    for (let i = 0; i < inputData.length; i++) {
                        const s = Math.max(-1, Math.min(1, inputData[i]));
                        pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                    }
                    
                    audioChunks.push(pcm16);
                };

                recognition.start();
                isRecording = true;

                document.getElementById('startBtn').disabled = true;
                document.getElementById('startBtn').classList.add('recording');
                document.getElementById('stopBtn').disabled = false;

                visualizeAudio();

            } catch (err) {
                alert('Microphone access denied: ' + err.message);
            }
        }

        async function stopRecording() {
            isRecording = false;

            if (recognition) recognition.stop();
            if (microphone) microphone.disconnect();
            if (scriptProcessor) scriptProcessor.disconnect();
            if (audioContext) audioContext.close();

            document.getElementById('startBtn').disabled = false;
            document.getElementById('startBtn').classList.remove('recording');
            document.getElementById('stopBtn').disabled = true;

            // Show analyzing message
            document.getElementById('transcriptDisplay').innerHTML = 
                '<div style="color: #667eea; font-weight: bold; text-align: center; padding: 40px;">🎤 Analyzing your voice...<br><small>This may take a few seconds</small></div>';

            // Combine audio chunks
            let totalLength = 0;
            audioChunks.forEach(chunk => totalLength += chunk.length);

            const combinedPCM = new Int16Array(totalLength);
            let offset = 0;
            audioChunks.forEach(chunk => {
                combinedPCM.set(chunk, offset);
                offset += chunk.length;
            });

            const wavBlob = createWavFile(combinedPCM, sampleRate, 1);
            
            const reader = new FileReader();
            reader.onloadend = async () => {
                try {
                    const response = await fetch('/save_audio', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            audio: reader.result,
                            transcript: currentTranscript.trim(),
                            quality: 8,
                            gameData: gameData
                        })
                    });

                    const result = await response.json();
                    
                    if (result.success && result.voice_analysis) {
                        showCelebrityMatch(result.voice_analysis);
                        updateLastResult(result.voice_analysis);
                    } else {
                        document.getElementById('transcriptDisplay').innerHTML = 
                            '<div style="color: #ef4444;">Analysis complete! Recording saved.</div>';
                    }

                    gameData.totalRecordings++;
                    gainXP(50);
                    saveGameData();

                } catch (error) {
                    console.error('Error:', error);
                    document.getElementById('transcriptDisplay').innerHTML = 
                        '<div style="color: #ef4444;">Error during analysis. Please try again.</div>';
                }
            };
            reader.readAsDataURL(wavBlob);
        }

        function showCelebrityMatch(analysis) {
            document.getElementById('celebName').textContent = analysis.celebrity_name;
            document.getElementById('matchPercent').textContent = analysis.match_percentage + '%';
            document.getElementById('genderValue').textContent = analysis.gender || '-';
            document.getElementById('ageValue').textContent = analysis.age_category || '-';
            
            if (analysis.voice_scores) {
                document.getElementById('bassValue').textContent = analysis.voice_scores.bass + '/10';
                document.getElementById('clarityValue').textContent = analysis.voice_scores.clarity + '/10';
            }
            
            document.getElementById('celebDescription').textContent = analysis.description || 'Your voice is unique!';
            document.getElementById('funFact').textContent = '💡 ' + (analysis.fun_fact || 'Keep recording to improve!');
            
            document.getElementById('celebrityModal').classList.add('show');
            
            // Bonus XP for high match
            if (analysis.match_percentage >= 90) {
                gainXP(100);
            } else if (analysis.match_percentage >= 80) {
                gainXP(50);
            }
        }

        function updateLastResult(analysis) {
            const resultDiv = document.getElementById('lastResult');
            resultDiv.innerHTML = `
                <div style="text-align: center;">
                    <div style="font-size: 1.5em; margin-bottom: 10px;">🌟</div>
                    <div style="font-weight: bold; color: #667eea; margin-bottom: 5px;">
                        ${analysis.celebrity_name}
                    </div>
                    <div style="font-size: 2em; font-weight: bold; color: #f59e0b;">
                        ${analysis.match_percentage}%
                    </div>
                    <div style="margin-top: 10px; font-size: 0.9em; color: #6b7280;">
                        ${analysis.gender} • ${analysis.age_category}
                    </div>
                </div>
            `;
        }

        function closeCelebrityModal() {
            document.getElementById('celebrityModal').classList.remove('show');
        }

        function visualizeAudio() {
            if (!isRecording) return;

            const bufferLength = analyser.frequencyBinCount;
            const dataArray = new Uint8Array(bufferLength);
            analyser.getByteFrequencyData(dataArray);

            const bars = document.querySelectorAll('.bar');
            const step = Math.floor(bufferLength / bars.length);

            bars.forEach((bar, index) => {
                const value = dataArray[index * step];
                const percent = (value / 255) * 100;
                bar.style.height = Math.max(2, percent) + '%';
            });

            requestAnimationFrame(visualizeAudio);
        }

        function createWavFile(pcmData, sampleRate, channels) {
            const buffer = new ArrayBuffer(44 + pcmData.length * 2);
            const view = new DataView(buffer);

            writeString(view, 0, 'RIFF');
            view.setUint32(4, 36 + pcmData.length * 2, true);
            writeString(view, 8, 'WAVE');
            writeString(view, 12, 'fmt ');
            view.setUint32(16, 16, true);
            view.setUint16(20, 1, true);
            view.setUint16(22, channels, true);
            view.setUint32(24, sampleRate, true);
            view.setUint32(28, sampleRate * channels * 2, true);
            view.setUint16(32, channels * 2, true);
            view.setUint16(34, 16, true);
            writeString(view, 36, 'data');
            view.setUint32(40, pcmData.length * 2, true);

            let offset = 44;
            for (let i = 0; i < pcmData.length; i++, offset += 2) {
                view.setInt16(offset, pcmData[i], true);
            }

            return new Blob([buffer], { type: 'audio/wav' });
        }

        function writeString(view, offset, string) {
            for (let i = 0; i < string.length; i++) {
                view.setUint8(offset + i, string.charCodeAt(i));
            }
        }
    </script>
</body>
</html>
"""


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("🎮 SPEECH QUEST - Voice Analysis Edition")
    print("=" * 70)
    print("\n✨ Features:")
    print("  🎙️  Direct WAV Recording (No FFmpeg)")
    print("  🌟 Celebrity Voice Matching with AI")
    print("  🎯 Gender & Age Detection")
    print("  📊 Voice Quality Scores (Bass, Clarity, Warmth, etc.)")
    print("  🎮 XP & Leveling System")
    print("  💬 Real-time Transcription")

    if GROQ_API_KEY:
        print("\n✅ Groq API configured - Voice analysis enabled!")
    else:
        print("\n⚠️  Groq API not configured - Limited functionality")
        print("💡 Create .env file with: GROQ_API_KEY=your_key")

    print(f"\n📁 Directories:")
    print(f"   Audio: {AUDIO_DIR}")
    print(f"   Reviews: {REVIEW_DIR}")
    print(f"   Game Data: {GAME_DIR}")

    print("\n🚀 Starting server...")
    print("🌐 Open: http://localhost:5000")
    print("\n" + "=" * 70 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5000)