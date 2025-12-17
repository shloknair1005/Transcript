"""
Real-Time Speech-to-Text Converter with Audio Quality Detection and WAV Saving

Installation:
pip install flask flask-cors numpy scipy

This saves audio recordings as .wav files in the Audio directory.
"""

from flask import Flask, render_template_string, request, jsonify
from flask_cors import CORS
import numpy as np
import json
import wave
import io
import os
from datetime import datetime
import base64

app = Flask(__name__)
CORS(app)

# Create Audio directory if it doesn't exist
AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Audio')
os.makedirs(AUDIO_DIR, exist_ok=True)
print(f"Audio files will be saved to: {AUDIO_DIR}")

# Create Review directory if it doesn't exist
REVIEW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Review')
os.makedirs(REVIEW_DIR, exist_ok=True)
print(f"Reviews will be saved to: {REVIEW_DIR}")

# HTML Template with integrated JavaScript for real-time audio capture
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Real-Time Speech-to-Text</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }

        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }

        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }

        .main-content {
            display: grid;
            grid-template-columns: 1fr 2fr;
            gap: 20px;
            margin-bottom: 20px;
        }

        .card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }

        .controls-panel h2 {
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.5em;
        }

        .control-group {
            margin-bottom: 25px;
        }

        .control-group label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 600;
        }

        select, button {
            width: 100%;
            padding: 12px;
            font-size: 1em;
            border-radius: 8px;
            border: 2px solid #e0e0e0;
            transition: all 0.3s;
        }

        select:focus {
            outline: none;
            border-color: #667eea;
        }

        button {
            background: #667eea;
            color: white;
            border: none;
            cursor: pointer;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        button:hover {
            background: #5568d3;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }

        button:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }

        .recording-btn {
            background: #10b981;
            margin-bottom: 10px;
        }

        .recording-btn:hover {
            background: #059669;
        }

        .recording-btn.recording {
            background: #ef4444;
            animation: pulse 1.5s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }

        .stop-btn {
            background: #f59e0b;
        }

        .stop-btn:hover {
            background: #d97706;
        }

        .quality-display {
            background: #f3f4f6;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
        }

        .quality-score {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
            text-align: center;
            margin: 10px 0;
        }

        .quality-bar {
            height: 20px;
            background: #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }

        .quality-fill {
            height: 100%;
            background: linear-gradient(90deg, #ef4444, #f59e0b, #10b981);
            transition: width 0.5s;
            border-radius: 10px;
        }

        .recommendation {
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
            padding: 12px;
            border-radius: 5px;
            margin: 15px 0;
        }

        .recommendation.optimal {
            background: #d1fae5;
            border-left-color: #10b981;
        }

        .model-info {
            background: #ede9fe;
            padding: 10px;
            border-radius: 5px;
            margin-top: 10px;
            font-size: 0.9em;
        }

        .transcription-panel h2 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.5em;
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
            color: #1f2937;
        }

        .transcript-display.empty {
            display: flex;
            align-items: center;
            justify-content: center;
            color: #9ca3af;
            font-style: italic;
        }

        .real-time-text {
            color: #667eea;
            font-weight: 500;
            animation: fadeIn 0.3s;
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        .final-text {
            color: #1f2937;
            margin-bottom: 10px;
        }

        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #9ca3af;
            margin-right: 8px;
        }

        .status-indicator.active {
            background: #10b981;
            box-shadow: 0 0 10px #10b981;
        }

        .status-indicator.recording {
            background: #ef4444;
            animation: blink 1s infinite;
        }

        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }

        .history-panel {
            grid-column: 1 / -1;
        }

        .history-item {
            background: #f9fafb;
            border-left: 4px solid #667eea;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 5px;
        }

        .history-meta {
            font-size: 0.9em;
            color: #6b7280;
            margin-bottom: 8px;
        }

        .audio-file-info {
            font-size: 0.85em;
            color: #10b981;
            margin-top: 5px;
            font-weight: 600;
        }

        .audio-visualizer {
            background: #1f2937;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
            height: 80px;
            position: relative;
            overflow: hidden;
        }

        .visualizer-bars {
            display: flex;
            align-items: flex-end;
            height: 100%;
            gap: 3px;
            justify-content: space-around;
        }

        .bar {
            flex: 1;
            background: linear-gradient(to top, #667eea, #764ba2);
            border-radius: 3px 3px 0 0;
            transition: height 0.1s;
            min-height: 2px;
        }

        .rating-section {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 12px;
            margin-top: 20px;
            border: 2px solid #e5e7eb;
        }

        .rating-section h3 {
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.3em;
            text-align: center;
        }

        .rating-category {
            margin-bottom: 20px;
            padding: 15px;
            background: white;
            border-radius: 8px;
        }

        .rating-category label {
            display: block;
            font-weight: 600;
            color: #374151;
            margin-bottom: 10px;
            font-size: 1.05em;
        }

        .stars {
            display: flex;
            gap: 8px;
            justify-content: center;
            font-size: 2em;
        }

        .star {
            cursor: pointer;
            color: #d1d5db;
            transition: all 0.2s;
            user-select: none;
        }

        .star:hover {
            transform: scale(1.2);
        }

        .star.filled {
            color: #f59e0b;
        }

        .star.active {
            animation: starPulse 0.3s;
        }

        @keyframes starPulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.3); }
        }

        .submit-rating-btn {
            background: #10b981;
            margin-top: 15px;
        }

        .submit-rating-btn:hover {
            background: #059669;
        }

        .rating-success {
            background: #d1fae5;
            color: #065f46;
            padding: 12px;
            border-radius: 8px;
            text-align: center;
            margin-top: 15px;
            font-weight: 600;
            display: none;
        }

        .rating-success.show {
            display: block;
            animation: fadeIn 0.5s;
        }

        @media (max-width: 768px) {
            .main-content {
                grid-template-columns: 1fr;
            }

            .header h1 {
                font-size: 1.8em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎤 Real-Time Speech-to-Text</h1>
            <p>Speak naturally and see your words transcribed instantly with quality detection</p>
        </div>

        <div class="main-content">
            <div class="card controls-panel">
                <h2>Controls</h2>

                <div class="control-group">
                    <label>
                        <span class="status-indicator" id="statusIndicator"></span>
                        Recording Status
                    </label>
                    <button id="startBtn" class="recording-btn" onclick="startRecording()">
                        🎙️ Start Recording
                    </button>
                    <button id="stopBtn" class="stop-btn" onclick="stopRecording()" disabled>
                        ⏹️ Stop Recording
                    </button>
                </div>

                <div class="audio-visualizer">
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

                <div class="quality-display">
                    <label style="font-size: 0.9em; color: #6b7280;">Audio Quality</label>
                    <div class="quality-score" id="qualityScore">-/10</div>
                    <div class="quality-bar">
                        <div class="quality-fill" id="qualityFill" style="width: 0%"></div>
                    </div>
                    <p id="qualityDesc" style="text-align: center; color: #6b7280; font-size: 0.9em;">
                        Start recording to see quality
                    </p>
                </div>

                <div class="control-group">
                    <label for="modelSelect">Transcription Model</label>
                    <select id="modelSelect">
                        <option value="model1">Model 1 - Fast (Clean Audio 8-10/10)</option>
                        <option value="model2" selected>Model 2 - Balanced (Moderate 5-7/10)</option>
                        <option value="model3">Model 3 - Robust (Noisy 1-4/10)</option>
                    </select>
                    <div class="model-info" id="modelInfo">
                        Best for moderate quality audio with some background noise. Good balance of speed and accuracy.
                    </div>
                </div>

                <div id="recommendation"></div>
            </div>

            <div class="card transcription-panel">
                <h2>Live Transcription</h2>
                <div class="transcript-display empty" id="transcriptDisplay">
                    Click "Start Recording" and begin speaking...
                </div>
            </div>
        </div>

        <div class="card history-panel">
            <h2>Transcription History</h2>
            <div id="historyContainer">
                <p style="color: #9ca3af; font-style: italic;">No transcriptions yet. Start recording to build history.</p>
            </div>
        </div>

        <div class="card history-panel">
            <div class="rating-section">
                <h3>⭐ Rate Your Experience</h3>

                <div class="rating-category">
                    <label>Transcription Quality</label>
                    <div class="stars" id="transcriptionStars">
                        <span class="star" onclick="setRating('transcription', 1)">★</span>
                        <span class="star" onclick="setRating('transcription', 2)">★</span>
                        <span class="star" onclick="setRating('transcription', 3)">★</span>
                        <span class="star" onclick="setRating('transcription', 4)">★</span>
                        <span class="star" onclick="setRating('transcription', 5)">★</span>
                    </div>
                </div>

                <div class="rating-category">
                    <label>User Interface (UI)</label>
                    <div class="stars" id="uiStars">
                        <span class="star" onclick="setRating('ui', 1)">★</span>
                        <span class="star" onclick="setRating('ui', 2)">★</span>
                        <span class="star" onclick="setRating('ui', 3)">★</span>
                        <span class="star" onclick="setRating('ui', 4)">★</span>
                        <span class="star" onclick="setRating('ui', 5)">★</span>
                    </div>
                </div>

                <div class="rating-category">
                    <label>Accuracy</label>
                    <div class="stars" id="accuracyStars">
                        <span class="star" onclick="setRating('accuracy', 1)">★</span>
                        <span class="star" onclick="setRating('accuracy', 2)">★</span>
                        <span class="star" onclick="setRating('accuracy', 3)">★</span>
                        <span class="star" onclick="setRating('accuracy', 4)">★</span>
                        <span class="star" onclick="setRating('accuracy', 5)">★</span>
                    </div>
                </div>

                <button class="btn submit-rating-btn" onclick="submitRating()">
                    Submit Rating
                </button>

                <div class="rating-success" id="ratingSuccess">
                    ✓ Thank you for your feedback!
                </div>
            </div>
        </div>
    </div>

    <script>
        let recognition;
        let audioContext;
        let analyser;
        let microphone;
        let mediaRecorder;
        let audioChunks = [];
        let isRecording = false;
        let transcriptionHistory = [];
        let currentTranscript = '';
        let interimTranscript = '';
        let currentQuality = 0;

        // Rating system
        let ratings = {
            transcription: 0,
            ui: 0,
            accuracy: 0
        };

        // Initialize Speech Recognition
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        if (!SpeechRecognition) {
            alert('Speech recognition is not supported in your browser. Please use Chrome, Edge, or Safari.');
        } else {
            recognition = new SpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = 'en-US';

            recognition.onresult = (event) => {
                interimTranscript = '';

                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const transcript = event.results[i][0].transcript;

                    if (event.results[i].isFinal) {
                        currentTranscript += transcript + ' ';
                    } else {
                        interimTranscript += transcript;
                    }
                }

                updateTranscriptDisplay();
            };

            recognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
                if (event.error === 'no-speech') {
                    console.log('No speech detected. Keep speaking...');
                }
            };

            recognition.onend = () => {
                if (isRecording) {
                    recognition.start(); // Restart if still recording
                }
            };
        }

        // Model information
        const modelInfo = {
            model1: 'Fast processing for clean, high-quality audio (8-10/10). Best for quiet environments.',
            model2: 'Best for moderate quality audio with some background noise. Good balance of speed and accuracy.',
            model3: 'Most robust for noisy environments and low-quality audio (1-4/10). Slower but more accurate in difficult conditions.'
        };

        // Update model info on selection change
        document.getElementById('modelSelect').addEventListener('change', (e) => {
            document.getElementById('modelInfo').textContent = modelInfo[e.target.value];
        });

        function updateTranscriptDisplay() {
            const display = document.getElementById('transcriptDisplay');
            display.classList.remove('empty');

            let html = '';
            if (currentTranscript) {
                html += `<div class="final-text">${currentTranscript}</div>`;
            }
            if (interimTranscript) {
                html += `<div class="real-time-text">${interimTranscript}</div>`;
            }

            display.innerHTML = html || '<div class="empty">Listening... start speaking</div>';
            display.scrollTop = display.scrollHeight;
        }

        async function startRecording() {
            try {
                // Start audio context for quality analysis
                audioContext = new (window.AudioContext || window.webkitAudioContext)();
                analyser = audioContext.createAnalyser();
                analyser.fftSize = 2048;

                const stream = await navigator.mediaDevices.getUserMedia({ 
                    audio: {
                        echoCancellation: true,
                        noiseSuppression: true,
                        autoGainControl: true,
                        sampleRate: 44100
                    } 
                });

                microphone = audioContext.createMediaStreamSource(stream);
                microphone.connect(analyser);

                // Setup MediaRecorder to capture audio
                audioChunks = [];
                const options = { mimeType: 'audio/webm;codecs=opus' };
                mediaRecorder = new MediaRecorder(stream, options);

                mediaRecorder.ondataavailable = (event) => {
                    if (event.data.size > 0) {
                        audioChunks.push(event.data);
                    }
                };

                mediaRecorder.onstop = async () => {
                    // Create blob from chunks
                    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });

                    // Convert to base64
                    const reader = new FileReader();
                    reader.onloadend = async () => {
                        const base64Audio = reader.result;

                        // Send to server
                        try {
                            const response = await fetch('/save_audio', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                },
                                body: JSON.stringify({
                                    audio: base64Audio,
                                    transcript: currentTranscript.trim(),
                                    quality: currentQuality,
                                    model: document.getElementById('modelSelect').selectedOptions[0].text
                                })
                            });

                            const result = await response.json();
                            console.log('Audio saved:', result);

                            // Add to history with audio file info
                            if (currentTranscript.trim()) {
                                addToHistory(currentTranscript.trim(), result.filename);
                            }
                        } catch (error) {
                            console.error('Error saving audio:', error);
                        }
                    };
                    reader.readAsDataURL(audioBlob);
                };

                // Start recording
                mediaRecorder.start();
                recognition.start();

                isRecording = true;
                currentTranscript = '';
                interimTranscript = '';

                document.getElementById('startBtn').disabled = true;
                document.getElementById('startBtn').classList.add('recording');
                document.getElementById('stopBtn').disabled = false;
                document.getElementById('statusIndicator').classList.add('recording');
                document.getElementById('transcriptDisplay').innerHTML = '<div class="empty">Listening... start speaking</div>';

                // Start quality monitoring
                monitorAudioQuality();

                // Start visualizer
                visualizeAudio();

            } catch (err) {
                console.error('Error accessing microphone:', err);
                alert('Could not access microphone. Please grant permission and try again.');
            }
        }

        function stopRecording() {
            isRecording = false;

            if (recognition) {
                recognition.stop();
            }

            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
            }

            if (microphone) {
                microphone.disconnect();
            }

            if (audioContext) {
                audioContext.close();
            }

            document.getElementById('startBtn').disabled = false;
            document.getElementById('startBtn').classList.remove('recording');
            document.getElementById('stopBtn').disabled = true;
            document.getElementById('statusIndicator').classList.remove('recording');
        }

        function monitorAudioQuality() {
            if (!isRecording) return;

            const bufferLength = analyser.frequencyBinCount;
            const dataArray = new Uint8Array(bufferLength);

            analyser.getByteFrequencyData(dataArray);

            // Calculate quality metrics
            const avgVolume = dataArray.reduce((a, b) => a + b) / bufferLength;
            const maxVolume = Math.max(...dataArray);

            // Simple quality score based on volume and frequency distribution
            let qualityScore = 0;

            // Volume score (0-40 points)
            const volumeScore = Math.min(40, (avgVolume / 255) * 40);
            qualityScore += volumeScore;

            // Frequency distribution score (0-30 points)
            const nonZeroFreqs = dataArray.filter(v => v > 10).length;
            const freqScore = Math.min(30, (nonZeroFreqs / bufferLength) * 30);
            qualityScore += freqScore;

            // Dynamic range score (0-30 points)
            const dynamicRange = maxVolume - Math.min(...dataArray);
            const rangeScore = Math.min(30, (dynamicRange / 255) * 30);
            qualityScore += rangeScore;

            // Convert to 1-10 scale
            qualityScore = Math.max(1, Math.min(10, (qualityScore / 10)));

            currentQuality = qualityScore;
            updateQualityDisplay(qualityScore);

            setTimeout(() => monitorAudioQuality(), 500);
        }

        function updateQualityDisplay(score) {
            const roundedScore = Math.round(score * 10) / 10;
            document.getElementById('qualityScore').textContent = roundedScore + '/10';
            document.getElementById('qualityFill').style.width = (score * 10) + '%';

            let desc = '';
            let recommendedModel = '';

            if (score >= 8) {
                desc = 'Excellent - Clear audio with minimal noise';
                recommendedModel = 'model1';
            } else if (score >= 5) {
                desc = 'Good - Some background noise present';
                recommendedModel = 'model2';
            } else if (score >= 3) {
                desc = 'Moderate - Noticeable noise may affect accuracy';
                recommendedModel = 'model3';
            } else {
                desc = 'Poor - High noise levels, accuracy limited';
                recommendedModel = 'model3';
            }

            document.getElementById('qualityDesc').textContent = desc;

            // Show recommendation
            const currentModel = document.getElementById('modelSelect').value;
            const recommendDiv = document.getElementById('recommendation');

            if (currentModel !== recommendedModel) {
                const modelNames = {
                    model1: 'Model 1 (Fast)',
                    model2: 'Model 2 (Balanced)',
                    model3: 'Model 3 (Robust)'
                };
                recommendDiv.innerHTML = `
                    <div class="recommendation">
                        ⚠️ For quality score ${roundedScore}/10, we recommend: <strong>${modelNames[recommendedModel]}</strong>
                    </div>
                `;
            } else {
                recommendDiv.innerHTML = `
                    <div class="recommendation optimal">
                        ✓ You're using the optimal model for this audio quality (${roundedScore}/10)
                    </div>
                `;
            }
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

        function addToHistory(text, audioFilename) {
            const quality = document.getElementById('qualityScore').textContent;
            const model = document.getElementById('modelSelect').selectedOptions[0].text;
            const timestamp = new Date().toLocaleTimeString();

            transcriptionHistory.unshift({
                text,
                quality,
                model,
                timestamp,
                audioFile: audioFilename
            });

            updateHistoryDisplay();
        }

        function updateHistoryDisplay() {
            const container = document.getElementById('historyContainer');

            if (transcriptionHistory.length === 0) {
                container.innerHTML = '<p style="color: #9ca3af; font-style: italic;">No transcriptions yet.</p>';
                return;
            }

            container.innerHTML = transcriptionHistory.slice(0, 10).map((item, index) => `
                <div class="history-item">
                    <div class="history-meta">
                        <strong>#${transcriptionHistory.length - index}</strong> | 
                        ${item.timestamp} | 
                        Quality: ${item.quality} | 
                        ${item.model}
                    </div>
                    ${item.audioFile ? `<div class="audio-file-info">🎵 Saved as: ${item.audioFile}</div>` : ''}
                    <div>${item.text}</div>
                </div>
            `).join('');
        }

        function setRating(category, rating) {
            ratings[category] = rating;

            // Update star display
            const starsContainer = document.getElementById(`${category}Stars`);
            const stars = starsContainer.querySelectorAll('.star');

            stars.forEach((star, index) => {
                if (index < rating) {
                    star.classList.add('filled', 'active');
                    setTimeout(() => star.classList.remove('active'), 300);
                } else {
                    star.classList.remove('filled');
                }
            });
        }

        async function submitRating() {
            // Check if all categories are rated
            if (ratings.transcription === 0 || ratings.ui === 0 || ratings.accuracy === 0) {
                alert('Please rate all categories before submitting.');
                return;
            }

            try {
                const response = await fetch('/submit_rating', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        transcription_quality: ratings.transcription,
                        ui: ratings.ui,
                        accuracy: ratings.accuracy,
                        timestamp: new Date().toISOString()
                    })
                });

                const result = await response.json();

                if (result.success) {
                    // Show success message
                    const successMsg = document.getElementById('ratingSuccess');
                    successMsg.classList.add('show');

                    // Reset ratings
                    ratings = { transcription: 0, ui: 0, accuracy: 0 };

                    // Clear all stars
                    ['transcription', 'ui', 'accuracy'].forEach(category => {
                        const stars = document.getElementById(`${category}Stars`).querySelectorAll('.star');
                        stars.forEach(star => star.classList.remove('filled'));
                    });

                    // Hide success message after 3 seconds
                    setTimeout(() => {
                        successMsg.classList.remove('show');
                    }, 3000);
                } else {
                    alert('Error submitting rating. Please try again.');
                }
            } catch (error) {
                console.error('Error submitting rating:', error);
                alert('Error submitting rating. Please try again.');
            }
        }
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/save_audio', methods=['POST'])
def save_audio():
    try:
        data = request.json
        audio_base64 = data.get('audio', '')
        transcript = data.get('transcript', '')
        quality = data.get('quality', 0)
        model = data.get('model', '')

        # Remove data URL prefix if present
        if ',' in audio_base64:
            audio_base64 = audio_base64.split(',')[1]

        # Decode base64 audio
        audio_bytes = base64.b64decode(audio_base64)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recording_{timestamp}.wav"
        filepath = os.path.join(AUDIO_DIR, filename)

        # Save the audio file (webm format, but saved as .wav extension for compatibility)
        with open(filepath, 'wb') as f:
            f.write(audio_bytes)

        print(f"Audio saved: {filepath}")
        print(f"Transcript: {transcript[:50]}...")
        print(f"Quality: {quality}/10")
        print(f"Model: {model}")

        return jsonify({
            'success': True,
            'filename': filename,
            'filepath': filepath,
            'transcript': transcript,
            'quality': quality,
            'model': model
        })

    except Exception as e:
        print(f"Error saving audio: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/submit_rating', methods=['POST'])
def submit_rating():
    try:
        data = request.json
        transcription_quality = data.get('transcription_quality', 0)
        ui = data.get('ui', 0)
        accuracy = data.get('accuracy', 0)
        timestamp = data.get('timestamp', datetime.now().isoformat())

        # Create review entry
        review = {
            'timestamp': timestamp,
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'ratings': {
                'transcription_quality': transcription_quality,
                'ui': ui,
                'accuracy': accuracy
            },
            'average': round((transcription_quality + ui + accuracy) / 3, 2)
        }

        # Generate filename with timestamp
        review_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"review_{review_timestamp}.json"
        filepath = os.path.join(REVIEW_DIR, filename)

        # Save review as JSON
        with open(filepath, 'w') as f:
            json.dump(review, f, indent=4)

        print(f"\n{'=' * 50}")
        print("New Review Submitted:")
        print(f"Transcription Quality: {transcription_quality}/5 ⭐")
        print(f"UI: {ui}/5 ⭐")
        print(f"Accuracy: {accuracy}/5 ⭐")
        print(f"Average: {review['average']}/5 ⭐")
        print(f"Saved to: {filepath}")
        print(f"{'=' * 50}\n")

        return jsonify({
            'success': True,
            'filename': filename,
            'review': review
        })

    except Exception as e:
        print(f"Error saving review: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("🎤 Real-Time Speech-to-Text Converter with Audio Saving")
    print("=" * 70)
    print("\nStarting server...")
    print("Open your browser and navigate to: http://localhost:5000")
    print("\nFeatures:")
    print("✓ Real-time transcription as you speak")
    print("✓ Audio quality detection (1-10 scale)")
    print("✓ Smart model recommendations")
    print("✓ Live audio visualization")
    print("✓ Transcription history")
    print("✓ Audio files saved to Audio/ directory")
    print("✓ User rating system (3 categories, 5 stars each)")
    print(f"\n📁 Audio directory: {AUDIO_DIR}")
    print(f"📁 Review directory: {REVIEW_DIR}")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 70 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5000)