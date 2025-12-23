"""
Gamified Real-Time Speech-to-Text Converter with Achievements, Rewards & Rating System

Installation:
pip install flask flask-cors numpy scipy

Features:
- XP and Level System
- Achievements & Badges
- Daily Challenges
- Leaderboard
- Streak Tracking
- User Rating System (5-star feedback)
- Audio saved as .wav files
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

# Create directories
AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Audio')
REVIEW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Review')
GAME_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'GameData')

for directory in [AUDIO_DIR, REVIEW_DIR, GAME_DIR]:
    os.makedirs(directory, exist_ok=True)

print(f"Audio files: {AUDIO_DIR}")
print(f"Reviews: {REVIEW_DIR}")
print(f"Game data: {GAME_DIR}")

# HTML Template with Gamification + Rating System
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Speech Quest - Gamified Transcription</title>
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
            max-width: 1400px;
            margin: 0 auto;
        }

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

        .header p {
            font-size: 1.2em;
            opacity: 0.9;
        }

        /* Game Stats Bar */
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
            position: relative;
            overflow: hidden;
        }

        .stat-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #f59e0b, #ef4444);
        }

        .stat-card.level::before {
            background: linear-gradient(90deg, #8b5cf6, #ec4899);
        }

        .stat-card.streak::before {
            background: linear-gradient(90deg, #10b981, #059669);
        }

        .stat-card.words::before {
            background: linear-gradient(90deg, #3b82f6, #2563eb);
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

        .level-progress {
            margin-top: 8px;
            background: #e5e7eb;
            height: 8px;
            border-radius: 4px;
            overflow: hidden;
        }

        .level-progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #8b5cf6, #ec4899);
            transition: width 0.5s;
            border-radius: 4px;
        }

        .xp-text {
            font-size: 0.75em;
            color: #6b7280;
            margin-top: 5px;
        }

        /* Main Content Grid */
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
            display: flex;
            align-items: center;
            gap: 10px;
        }

        /* Controls Panel */
        .control-group {
            margin-bottom: 20px;
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

        /* Daily Challenges */
        .challenges {
            background: #f9fafb;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 20px;
        }

        .challenge-item {
            background: white;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 10px;
            border-left: 4px solid #667eea;
        }

        .challenge-item.completed {
            border-left-color: #10b981;
            background: #d1fae5;
        }

        .challenge-title {
            font-weight: 600;
            color: #374151;
            margin-bottom: 5px;
        }

        .challenge-progress {
            font-size: 0.85em;
            color: #6b7280;
        }

        .challenge-reward {
            float: right;
            color: #f59e0b;
            font-weight: bold;
        }

        /* Achievements Panel */
        .achievements-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            max-height: 600px;
            overflow-y: auto;
        }

        .achievement {
            background: #f9fafb;
            padding: 12px;
            border-radius: 10px;
            text-align: center;
            transition: all 0.3s;
            border: 2px solid transparent;
        }

        .achievement.unlocked {
            background: linear-gradient(135deg, #fef3c7, #fde68a);
            border-color: #f59e0b;
            box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
        }

        .achievement.locked {
            opacity: 0.5;
            filter: grayscale(1);
        }

        .achievement-icon {
            font-size: 2.5em;
            margin-bottom: 8px;
        }

        .achievement-name {
            font-weight: 600;
            color: #374151;
            font-size: 0.9em;
            margin-bottom: 4px;
        }

        .achievement-desc {
            font-size: 0.75em;
            color: #6b7280;
        }

        .achievement-xp {
            font-size: 0.8em;
            color: #8b5cf6;
            font-weight: bold;
            margin-top: 5px;
        }

        /* Transcription Panel */
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

        .real-time-text {
            color: #667eea;
            font-weight: 500;
            animation: fadeIn 0.3s;
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        /* Rating Section */
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

        /* XP Gain Animation */
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

        .xp-popup.show {
            display: block;
        }

        @keyframes xpBounce {
            0%, 100% { transform: translate(-50%, -50%) scale(1); }
            50% { transform: translate(-50%, -50%) scale(1.2); }
        }

        /* Level Up Modal */
        .level-up-modal {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.8);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 2000;
        }

        .level-up-modal.show {
            display: flex;
        }

        .level-up-content {
            background: white;
            padding: 50px;
            border-radius: 20px;
            text-align: center;
            animation: levelUpScale 0.5s;
        }

        @keyframes levelUpScale {
            0% { transform: scale(0.5); opacity: 0; }
            100% { transform: scale(1); opacity: 1; }
        }

        .level-up-title {
            font-size: 3em;
            color: #8b5cf6;
            margin-bottom: 20px;
            text-shadow: 2px 2px 4px rgba(139, 92, 246, 0.3);
        }

        .level-up-number {
            font-size: 5em;
            font-weight: bold;
            background: linear-gradient(135deg, #8b5cf6, #ec4899);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 20px 0;
        }

        .level-up-rewards {
            background: #f9fafb;
            padding: 20px;
            border-radius: 10px;
            margin-top: 20px;
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

        .quality-display {
            background: #f3f4f6;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
        }

        .quality-score {
            font-size: 1.8em;
            font-weight: bold;
            color: #667eea;
            text-align: center;
            margin: 10px 0;
        }

        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #9ca3af;
            margin-right: 8px;
        }

        .status-indicator.recording {
            background: #ef4444;
            animation: blink 1s infinite;
        }

        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }

        @media (max-width: 1200px) {
            .main-content {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎮 Speech Quest</h1>
            <p>Level up your voice! Earn XP, unlock achievements, and master transcription</p>
        </div>

        <!-- Game Stats Bar -->
        <div class="game-stats-bar">
            <div class="stat-card level">
                <div class="stat-label">Level</div>
                <div class="stat-value" id="playerLevel">1</div>
                <div class="level-progress">
                    <div class="level-progress-fill" id="levelProgressBar" style="width: 0%"></div>
                </div>
                <div class="xp-text" id="xpText">0 / 100 XP</div>
            </div>

            <div class="stat-card">
                <div class="stat-label">Total XP</div>
                <div class="stat-value" id="totalXP">0</div>
            </div>

            <div class="stat-card streak">
                <div class="stat-label">🔥 Streak</div>
                <div class="stat-value" id="streakDays">0</div>
            </div>

            <div class="stat-card words">
                <div class="stat-label">Words Spoken</div>
                <div class="stat-value" id="totalWords">0</div>
            </div>

            <div class="stat-card">
                <div class="stat-label">Achievements</div>
                <div class="stat-value"><span id="unlockedCount">0</span>/<span id="totalAchievements">15</span></div>
            </div>
        </div>

        <!-- Main Content -->
        <div class="main-content">
            <!-- Left Panel: Controls & Challenges -->
            <div class="card controls-panel">
                <h2>🎯 Controls</h2>

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

                <div style="background: #f3f4f6; border-radius: 12px; padding: 20px; margin: 15px 0; border: 2px solid #e5e7eb;">
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                        <span style="font-size: 1.2em;">🎵</span>
                        <span style="color: #667eea; font-weight: 600; font-size: 1em;">Voice Output</span>
                        <div style="margin-left: auto; display: flex; gap: 8px;">
                            <button onclick="downloadAudio()" style="background: transparent; border: none; padding: 5px; cursor: pointer; font-size: 1.1em;" title="Download">📥</button>
                            <button onclick="shareAudio()" style="background: transparent; border: none; padding: 5px; cursor: pointer; font-size: 1.1em;" title="Share">🔗</button>
                        </div>
                    </div>
                    
                    <div id="waveformContainer" style="background: white; border-radius: 8px; padding: 15px; margin-bottom: 15px; height: 80px; display: none; position: relative; overflow: hidden;">
                        <canvas id="waveformCanvas" style="width: 100%; height: 100%;"></canvas>
                        <div id="playheadLine" style="position: absolute; top: 0; left: 0; width: 2px; height: 100%; background: #667eea; display: none;"></div>
                    </div>
                    
                    <div id="noAudioMessage" style="background: white; border-radius: 8px; padding: 30px; text-align: center; color: #9ca3af; font-size: 0.9em;">
                        No recording available. Start recording to hear playback.
                    </div>
                    
                    <div id="audioControls" style="display: none;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                            <span id="currentTime" style="font-size: 0.85em; color: #6b7280; font-weight: 500;">0:00</span>
                            <span id="totalTime" style="font-size: 0.85em; color: #6b7280; font-weight: 500;">0:00</span>
                        </div>
                        
                        <div style="display: flex; justify-content: center; align-items: center; gap: 15px;">
                            <button onclick="changeVolume()" id="volumeBtn" style="background: transparent; border: none; padding: 8px; cursor: pointer; font-size: 1.3em;" title="Volume">🔊</button>
                            
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <button onclick="skipBackward()" style="background: #e5e7eb; border: none; padding: 10px 15px; border-radius: 8px; cursor: pointer; font-size: 1.2em; transition: all 0.2s;" onmouseover="this.style.background='#d1d5db'" onmouseout="this.style.background='#e5e7eb'">⏮️</button>
                                
                                <button onclick="togglePlayPause()" id="playPauseBtn" style="background: #667eea; border: none; padding: 15px 20px; border-radius: 50%; cursor: pointer; font-size: 1.5em; transition: all 0.2s; box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);" onmouseover="this.style.background='#5568d3'" onmouseout="this.style.background='#667eea'">▶️</button>
                                
                                <button onclick="skipForward()" style="background: #e5e7eb; border: none; padding: 10px 15px; border-radius: 8px; cursor: pointer; font-size: 1.2em; transition: all 0.2s;" onmouseover="this.style.background='#d1d5db'" onmouseout="this.style.background='#e5e7eb'">⏭️</button>
                            </div>
                            
                            <div style="display: flex; align-items: center; gap: 5px;">
                                <button onclick="changePlaybackSpeed()" id="speedBtn" style="background: #e5e7eb; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 0.85em; font-weight: 600; color: #667eea; transition: all 0.2s;" onmouseover="this.style.background='#d1d5db'" onmouseout="this.style.background='#e5e7eb'">1.0x</button>
                            </div>
                        </div>
                    </div>
                    
                    <audio id="audioPlayer" style="display: none;">
                        Your browser does not support the audio element.
                    </audio>
                </div>

                <div class="quality-display">
                    <label style="font-size: 0.9em; color: #6b7280;">Audio Quality</label>
                    <div class="quality-score" id="qualityScore">-/10</div>
                </div>

                <h2 style="margin-top: 30px;">📋 Daily Challenges</h2>
                <div class="challenges" id="challengesContainer">
                    <!-- Populated by JS -->
                </div>
            </div>

            <!-- Center Panel: Transcription -->
            <div class="card transcription-panel">
                <h2>💬 Live Transcription</h2>
                <div class="transcript-display" id="transcriptDisplay">
                    Click "Start Recording" to begin your quest...
                </div>

                <div style="margin-top: 20px; padding: 15px; background: #f9fafb; border-radius: 10px;">
                    <h3 style="color: #667eea; margin-bottom: 10px;">🎁 Quick Tips</h3>
                    <ul style="color: #6b7280; font-size: 0.9em; line-height: 1.8;">
                        <li>Speak clearly to earn quality bonuses (+50 XP)</li>
                        <li>Complete daily challenges for massive XP</li>
                        <li>Maintain your streak for bonus multipliers</li>
                        <li>Unlock all achievements to become a Speech Master!</li>
                    </ul>
                </div>
            </div>

            <!-- Right Panel: Achievements -->
            <div class="card achievements-panel">
                <h2>🏆 Achievements</h2>
                <div class="achievements-grid" id="achievementsGrid">
                    <!-- Populated by JS -->
                </div>
            </div>
        </div>

        <!-- Rating Section -->
        <div class="card">
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
                    ✓ Thank you for your feedback! +100 Bonus XP!
                </div>
            </div>
        </div>
    </div>

    <!-- XP Popup -->
    <div class="xp-popup" id="xpPopup">
        +<span id="xpAmount">0</span> XP!
    </div>

    <!-- Level Up Modal -->
    <div class="level-up-modal" id="levelUpModal">
        <div class="level-up-content">
            <div class="level-up-title">🎉 LEVEL UP! 🎉</div>
            <div class="level-up-number" id="newLevel">2</div>
            <div class="level-up-rewards">
                <h3 style="color: #667eea; margin-bottom: 15px;">New Rewards Unlocked!</h3>
                <div id="levelRewards"></div>
            </div>
            <button onclick="closeLevelUpModal()" style="margin-top: 20px; background: #8b5cf6;">
                Continue Quest
            </button>
        </div>
    </div>

    <script>
        // Game State
        let gameData = {
            level: 1,
            xp: 0,
            totalWords: 0,
            streak: 0,
            lastPlayDate: null,
            achievements: {},
            dailyChallenges: {},
            totalRecordings: 0,
            highQualityRecordings: 0
        };

        // Rating system
        let ratings = {
            transcription: 0,
            ui: 0,
            accuracy: 0
        };

        // Achievements Definition
        const achievements = [
            { id: 'first_words', name: 'First Words', desc: 'Record your first transcription', icon: '🎤', xp: 50, condition: () => gameData.totalRecordings >= 1 },
            { id: 'chatterbox', name: 'Chatterbox', desc: 'Speak 100 words', icon: '💬', xp: 100, condition: () => gameData.totalWords >= 100 },
            { id: 'speaker_pro', name: 'Speaker Pro', desc: 'Speak 500 words', icon: '🗣️', xp: 250, condition: () => gameData.totalWords >= 500 },
            { id: 'voice_master', name: 'Voice Master', desc: 'Speak 1000 words', icon: '🎙️', xp: 500, condition: () => gameData.totalWords >= 1000 },
            { id: 'quality_first', name: 'Quality First', desc: 'Achieve 8+ audio quality', icon: '⭐', xp: 150, condition: () => gameData.highQualityRecordings >= 1 },
            { id: 'perfectionist', name: 'Perfectionist', desc: 'Get 5 high-quality recordings', icon: '💎', xp: 300, condition: () => gameData.highQualityRecordings >= 5 },
            { id: 'dedicated', name: 'Dedicated', desc: 'Record for 3 days in a row', icon: '🔥', xp: 200, condition: () => gameData.streak >= 3 },
            { id: 'unstoppable', name: 'Unstoppable', desc: '7 day streak', icon: '🚀', xp: 500, condition: () => gameData.streak >= 7 },
            { id: 'marathon', name: 'Marathon', desc: 'Complete 10 recordings', icon: '🏃', xp: 300, condition: () => gameData.totalRecordings >= 10 },
            { id: 'challenge_seeker', name: 'Challenge Seeker', desc: 'Complete a daily challenge', icon: '🎯', xp: 200, condition: () => Object.values(gameData.dailyChallenges).some(c => c.completed) },
            { id: 'overachiever', name: 'Overachiever', desc: 'Complete all daily challenges', icon: '🌟', xp: 500, condition: () => Object.values(gameData.dailyChallenges).filter(c => c.completed).length >= 3 },
            { id: 'early_bird', name: 'Early Bird', desc: 'Record before 9 AM', icon: '🌅', xp: 100, condition: () => false },
            { id: 'night_owl', name: 'Night Owl', desc: 'Record after 9 PM', icon: '🦉', xp: 100, condition: () => false },
            { id: 'speed_talker', name: 'Speed Talker', desc: 'Speak 50+ words in one session', icon: '⚡', xp: 150, condition: () => false },
            { id: 'speech_legend', name: 'Speech Legend', desc: 'Reach level 10', icon: '👑', xp: 1000, condition: () => gameData.level >= 10 }
        ];

        // Daily Challenges
        const dailyChallenges = [
            { id: 'daily_words', name: 'Daily Wordsmith', desc: 'Speak 200 words today', target: 200, current: 0, xp: 300, icon: '📝' },
            { id: 'daily_quality', name: 'Quality Voice', desc: 'Achieve 7+ quality twice', target: 2, current: 0, xp: 250, icon: '🎵' },
            { id: 'daily_sessions', name: 'Triple Threat', desc: 'Complete 3 recordings today', target: 3, current: 0, xp: 200, icon: '🎯' }
        ];

        // Speech Recognition
        let recognition;
        let audioContext;
        let analyser;
        let microphone;
        let mediaRecorder;
        let audioChunks = [];
        let isRecording = false;
        let currentTranscript = '';
        let interimTranscript = '';
        let currentQuality = 0;
        let sessionWordCount = 0;
        let audioPlayer;
        let currentAudioBlob = null;
        let playbackSpeed = 1.0;
        let volumeLevel = 1.0;
        let isPlaying = false;

        // Initialize
        window.onload = () => {
            loadGameData();
            initSpeechRecognition();
            updateUI();
            initDailyChallenges();
            renderAchievements();
            initAudioPlayer();
        };

        function initAudioPlayer() {
            audioPlayer = document.getElementById('audioPlayer');
            
            audioPlayer.addEventListener('timeupdate', updatePlaybackTime);
            audioPlayer.addEventListener('ended', () => {
                isPlaying = false;
                document.getElementById('playPauseBtn').textContent = '😃';
                document.getElementById('playheadLine').style.display = 'none';
            });
            audioPlayer.addEventListener('loadedmetadata', () => {
                const duration = formatTime(audioPlayer.duration);
                document.getElementById('totalTime').textContent = duration;
                drawWaveform();
            });
        }

        function formatTime(seconds) {
            if (isNaN(seconds)) return '0:00';
            const mins = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return `${mins}:${secs.toString().padStart(2, '0')}`;
        }

        function updatePlaybackTime() {
            const currentTime = formatTime(audioPlayer.currentTime);
            document.getElementById('currentTime').textContent = currentTime;
            
            // Update playhead position
            if (audioPlayer.duration) {
                const progress = (audioPlayer.currentTime / audioPlayer.duration) * 100;
                const playheadLine = document.getElementById('playheadLine');
                playheadLine.style.left = progress + '%';
                if (isPlaying) {
                    playheadLine.style.display = 'block';
                }
            }
        }

        function drawWaveform() {
            const canvas = document.getElementById('waveformCanvas');
            const ctx = canvas.getContext('2d');
            
            // Set canvas size
            canvas.width = canvas.offsetWidth;
            canvas.height = canvas.offsetHeight;
            
            // Clear canvas
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // Draw waveform bars
            const barCount = 100;
            const barWidth = canvas.width / barCount;
            const maxHeight = canvas.height;
            
            ctx.fillStyle = '#667eea';
            
            for (let i = 0; i < barCount; i++) {
                // Generate random heights for demo waveform
                const height = Math.random() * maxHeight * 0.8 + maxHeight * 0.1;
                const x = i * barWidth;
                const y = (maxHeight - height) / 2;
                
                ctx.fillRect(x, y, barWidth - 1, height);
            }
        }

        function togglePlayPause() {
            if (!audioPlayer.src) return;
            
            if (isPlaying) {
                audioPlayer.pause();
                document.getElementById('playPauseBtn').textContent = '😃';
                isPlaying = false;
            } else {
                audioPlayer.play();
                document.getElementById('playPauseBtn').textContent = '😓';
                isPlaying = true;
            }
        }

        function skipBackward() {
            if (audioPlayer.src) {
                audioPlayer.currentTime = Math.max(0, audioPlayer.currentTime - 10);
            }
        }

        function skipForward() {
            if (audioPlayer.src) {
                audioPlayer.currentTime = Math.min(audioPlayer.duration, audioPlayer.currentTime + 10);
            }
        }

        function changePlaybackSpeed() {
            const speeds = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0];
            const currentIndex = speeds.indexOf(playbackSpeed);
            const nextIndex = (currentIndex + 1) % speeds.length;
            playbackSpeed = speeds[nextIndex];
            
            audioPlayer.playbackRate = playbackSpeed;
            document.getElementById('speedBtn').textContent = playbackSpeed.toFixed(1) + 'x';
        }

        function changeVolume() {
            const volumes = [1.0, 0.5, 0.0];
            const icons = ['🔊', '🔉', '🔇'];
            const currentIndex = volumes.indexOf(volumeLevel);
            const nextIndex = (currentIndex + 1) % volumes.length;
            volumeLevel = volumes[nextIndex];
            
            audioPlayer.volume = volumeLevel;
            document.getElementById('volumeBtn').textContent = icons[nextIndex];
        }

        function downloadAudio() {
            if (!currentAudioBlob) {
                alert('No audio recording available to download.');
                return;
            }
            
            const url = URL.createObjectURL(currentAudioBlob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `speech-quest-${new Date().getTime()}.webm`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            // Bonus XP for downloading!
            gainXP(25, 'Downloaded recording!');
        }

        function shareAudio() {
            if (!currentAudioBlob) {
                alert('No audio recording available to share.');
                return;
            }
            
            if (navigator.share) {
                const file = new File([currentAudioBlob], 'speech-quest-recording.webm', { type: 'audio/webm' });
                navigator.share({
                    title: 'My Speech Quest Recording',
                    text: 'Check out my recording from Speech Quest!',
                    files: [file]
                }).catch(err => console.log('Error sharing:', err));
            } else {
                alert('Sharing is not supported on this browser. Use the download button instead!');
            }
        }

        function loadGameData() {
            const saved = localStorage.getItem('speechQuestData');
            if (saved) {
                gameData = JSON.parse(saved);
                checkStreak();
            } else {
                initDailyChallenges();
            }
        }

        function saveGameData() {
            localStorage.setItem('speechQuestData', JSON.stringify(gameData));
        }

        function checkStreak() {
            const today = new Date().toDateString();
            const lastPlay = gameData.lastPlayDate;

            if (lastPlay) {
                const lastDate = new Date(lastPlay);
                const dayDiff = Math.floor((new Date(today) - lastDate) / (1000 * 60 * 60 * 24));

                if (dayDiff === 1) {
                    gameData.streak++;
                } else if (dayDiff > 1) {
                    gameData.streak = 1;
                }
            } else {
                gameData.streak = 1;
            }

            gameData.lastPlayDate = today;
            saveGameData();
        }

        function initDailyChallenges() {
            gameData.dailyChallenges = {};
            dailyChallenges.forEach(challenge => {
                gameData.dailyChallenges[challenge.id] = {
                    ...challenge,
                    completed: false
                };
            });
            renderChallenges();
        }

        function renderChallenges() {
            const container = document.getElementById('challengesContainer');
            container.innerHTML = Object.values(gameData.dailyChallenges).map(challenge => `
                <div class="challenge-item ${challenge.completed ? 'completed' : ''}">
                    <div class="challenge-title">
                        ${challenge.icon} ${challenge.name}
                        <span class="challenge-reward">+${challenge.xp} XP</span>
                    </div>
                    <div class="challenge-progress">
                        ${challenge.desc} - ${challenge.current}/${challenge.target}
                        ${challenge.completed ? '✅' : ''}
                    </div>
                </div>
            `).join('');
        }

        function renderAchievements() {
            const grid = document.getElementById('achievementsGrid');
            grid.innerHTML = achievements.map(achievement => {
                const unlocked = gameData.achievements[achievement.id] || false;
                return `
                    <div class="achievement ${unlocked ? 'unlocked' : 'locked'}">
                        <div class="achievement-icon">${achievement.icon}</div>
                        <div class="achievement-name">${achievement.name}</div>
                        <div class="achievement-desc">${achievement.desc}</div>
                        <div class="achievement-xp">${unlocked ? '✅' : '+' + achievement.xp + ' XP'}</div>
                    </div>
                `;
            }).join('');

            const unlockedCount = Object.values(gameData.achievements).filter(v => v).length;
            document.getElementById('unlockedCount').textContent = unlockedCount;
            document.getElementById('totalAchievements').textContent = achievements.length;
        }

        function updateUI() {
            document.getElementById('playerLevel').textContent = gameData.level;
            document.getElementById('totalXP').textContent = gameData.xp;
            document.getElementById('streakDays').textContent = gameData.streak;
            document.getElementById('totalWords').textContent = gameData.totalWords;

            const xpForNextLevel = gameData.level * 100;
            const currentLevelXP = gameData.xp % xpForNextLevel;
            const progress = (currentLevelXP / xpForNextLevel) * 100;

            document.getElementById('levelProgressBar').style.width = progress + '%';
            document.getElementById('xpText').textContent = `${currentLevelXP} / ${xpForNextLevel} XP`;

            renderAchievements();
        }

        function gainXP(amount, reason) {
            gameData.xp += amount;

            document.getElementById('xpAmount').textContent = amount;
            const popup = document.getElementById('xpPopup');
            popup.classList.add('show');
            setTimeout(() => popup.classList.remove('show'), 1500);

            const xpForNextLevel = gameData.level * 100;
            if (gameData.xp >= gameData.level * xpForNextLevel) {
                levelUp();
            }

            updateUI();
            saveGameData();
        }

        function levelUp() {
            gameData.level++;
            
            document.getElementById('newLevel').textContent = gameData.level;
            document.getElementById('levelRewards').innerHTML = `
                <p style="color: #6b7280; margin-bottom: 10px;">
                    🎊 XP Multiplier increased!<br>
                    🎁 New achievements unlocked!<br>
                    ⭐ ${gameData.level * 10} bonus XP!
                </p>
            `;
            
            gameData.xp += gameData.level * 10;
            
            document.getElementById('levelUpModal').classList.add('show');
            
            updateUI();
            saveGameData();
        }

        function closeLevelUpModal() {
            document.getElementById('levelUpModal').classList.remove('show');
        }

        function checkAchievements() {
            achievements.forEach(achievement => {
                if (!gameData.achievements[achievement.id] && achievement.condition()) {
                    unlockAchievement(achievement);
                }
            });
        }

        function unlockAchievement(achievement) {
            gameData.achievements[achievement.id] = true;
            gainXP(achievement.xp, `Achievement: ${achievement.name}`);
            
            alert(`🎉 Achievement Unlocked!\n${achievement.icon} ${achievement.name}\n+${achievement.xp} XP`);
            
            renderAchievements();
            saveGameData();
        }

        function updateChallenges(type, value) {
            const challenges = gameData.dailyChallenges;
            
            if (type === 'words' && challenges.daily_words && !challenges.daily_words.completed) {
                challenges.daily_words.current += value;
                if (challenges.daily_words.current >= challenges.daily_words.target) {
                    challenges.daily_words.completed = true;
                    gainXP(challenges.daily_words.xp, 'Daily Challenge Complete!');
                }
            }
            
            if (type === 'quality' && challenges.daily_quality && !challenges.daily_quality.completed) {
                if (value >= 7) {
                    challenges.daily_quality.current++;
                    if (challenges.daily_quality.current >= challenges.daily_quality.target) {
                        challenges.daily_quality.completed = true;
                        gainXP(challenges.daily_quality.xp, 'Daily Challenge Complete!');
                    }
                }
            }
            
            if (type === 'session' && challenges.daily_sessions && !challenges.daily_sessions.completed) {
                challenges.daily_sessions.current++;
                if (challenges.daily_sessions.current >= challenges.daily_sessions.target) {
                    challenges.daily_sessions.completed = true;
                    gainXP(challenges.daily_sessions.xp, 'Daily Challenge Complete!');
                }
            }
            
            renderChallenges();
            saveGameData();
        }

        function initSpeechRecognition() {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

            if (!SpeechRecognition) {
                alert('Speech recognition is not supported in your browser. Please use Chrome, Edge, or Safari.');
                return;
            }

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
                        
                        const words = transcript.trim().split(/\s+/).length;
                        sessionWordCount += words;
                        gameData.totalWords += words;
                        
                        gainXP(words, `Spoke ${words} words`);
                        
                        updateChallenges('words', words);
                        
                        updateUI();
                    } else {
                        interimTranscript += transcript;
                    }
                }

                updateTranscriptDisplay();
            };

            recognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
            };

            recognition.onend = () => {
                if (isRecording) {
                    recognition.start();
                }
            };
        }

        function updateTranscriptDisplay() {
            const display = document.getElementById('transcriptDisplay');
            
            let html = '';
            if (currentTranscript) {
                html += `<div class="final-text">${currentTranscript}</div>`;
            }
            if (interimTranscript) {
                html += `<div class="real-time-text">${interimTranscript}</div>`;
            }

            display.innerHTML = html || '<div style="color: #9ca3af;">Listening... start speaking</div>';
            display.scrollTop = display.scrollHeight;
        }

        async function startRecording() {
            try {
                sessionWordCount = 0;
                
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

                audioChunks = [];
                const options = { mimeType: 'audio/webm;codecs=opus' };
                mediaRecorder = new MediaRecorder(stream, options);

                mediaRecorder.ondataavailable = (event) => {
                    if (event.data.size > 0) {
                        audioChunks.push(event.data);
                    }
                };

                mediaRecorder.onstop = async () => {
                    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                    currentAudioBlob = audioBlob;
                    
                    // Create URL for audio playback
                    const audioUrl = URL.createObjectURL(audioBlob);
                    audioPlayer.src = audioUrl;
                    
                    // Show audio controls and waveform
                    document.getElementById('audioControls').style.display = 'block';
                    document.getElementById('waveformContainer').style.display = 'block';
                    document.getElementById('noAudioMessage').style.display = 'none';
                    
                    const reader = new FileReader();
                    
                    reader.onloadend = async () => {
                        const base64Audio = reader.result;

                        try {
                            const response = await fetch('/save_audio', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    audio: base64Audio,
                                    transcript: currentTranscript.trim(),
                                    quality: currentQuality,
                                    gameData: gameData
                                })
                            });

                            const result = await response.json();
                            console.log('Audio saved:', result);
                        } catch (error) {
                            console.error('Error saving audio:', error);
                        }
                    };
                    reader.readAsDataURL(audioBlob);
                };

                mediaRecorder.start();
                recognition.start();

                isRecording = true;
                currentTranscript = '';
                interimTranscript = '';

                document.getElementById('startBtn').disabled = true;
                document.getElementById('startBtn').classList.add('recording');
                document.getElementById('stopBtn').disabled = false;
                document.getElementById('statusIndicator').classList.add('recording');

                monitorAudioQuality();
                checkTimeBasedAchievements();

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

            gameData.totalRecordings++;
            
            gainXP(20, 'Recording completed');
            
            if (currentQuality >= 8) {
                gameData.highQualityRecordings++;
                gainXP(50, 'High quality bonus!');
                updateChallenges('quality', currentQuality);
            }
            
            updateChallenges('session', 1);
            
            if (sessionWordCount >= 50 && !gameData.achievements.speed_talker) {
                unlockAchievement(achievements.find(a => a.id === 'speed_talker'));
            }
            
            checkAchievements();
            
            updateUI();
            saveGameData();
        }

        function checkTimeBasedAchievements() {
            const hour = new Date().getHours();
            
            if (hour < 9 && !gameData.achievements.early_bird) {
                unlockAchievement(achievements.find(a => a.id === 'early_bird'));
            }
            
            if (hour >= 21 && !gameData.achievements.night_owl) {
                unlockAchievement(achievements.find(a => a.id === 'night_owl'));
            }
        }

        function monitorAudioQuality() {
            if (!isRecording) return;

            const bufferLength = analyser.frequencyBinCount;
            const dataArray = new Uint8Array(bufferLength);
            analyser.getByteFrequencyData(dataArray);

            const avgVolume = dataArray.reduce((a, b) => a + b) / bufferLength;
            const maxVolume = Math.max(...dataArray);

            let qualityScore = 0;
            qualityScore += Math.min(40, (avgVolume / 255) * 40);
            
            const nonZeroFreqs = dataArray.filter(v => v > 10).length;
            qualityScore += Math.min(30, (nonZeroFreqs / bufferLength) * 30);
            
            const dynamicRange = maxVolume - Math.min(...dataArray);
            qualityScore += Math.min(30, (dynamicRange / 255) * 30);

            currentQuality = Math.max(1, Math.min(10, (qualityScore / 10)));
            document.getElementById('qualityScore').textContent = currentQuality.toFixed(1) + '/10';

            setTimeout(() => monitorAudioQuality(), 500);
        }

        // Rating System Functions
        function setRating(category, rating) {
            ratings[category] = rating;

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
                        timestamp: new Date().toISOString(),
                        gameData: {
                            level: gameData.level,
                            xp: gameData.xp,
                            totalWords: gameData.totalWords
                        }
                    })
                });

                const result = await response.json();

                if (result.success) {
                    const successMsg = document.getElementById('ratingSuccess');
                    successMsg.classList.add('show');

                    // Bonus XP for providing feedback!
                    gainXP(100, 'Feedback bonus!');

                    ratings = { transcription: 0, ui: 0, accuracy: 0 };

                    ['transcription', 'ui', 'accuracy'].forEach(category => {
                        const stars = document.getElementById(`${category}Stars`).querySelectorAll('.star');
                        stars.forEach(star => star.classList.remove('filled'));
                    });

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
        game_data = data.get('gameData', {})

        if ',' in audio_base64:
            audio_base64 = audio_base64.split(',')[1]

        audio_bytes = base64.b64decode(audio_base64)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recording_{timestamp}.wav"
        filepath = os.path.join(AUDIO_DIR, filename)

        with open(filepath, 'wb') as f:
            f.write(audio_bytes)

        # Save game data
        game_filename = f"game_state_{timestamp}.json"
        game_filepath = os.path.join(GAME_DIR, game_filename)
        
        with open(game_filepath, 'w') as f:
            json.dump({
                'timestamp': timestamp,
                'transcript': transcript,
                'quality': quality,
                'gameData': game_data
            }, f, indent=4)

        print(f"\n{'='*50}")
        print(f"🎮 Recording Saved - Level {game_data.get('level', 1)}")
        print(f"Audio: {filepath}")
        print(f"Quality: {quality}/10")
        print(f"XP: {game_data.get('xp', 0)}")
        print(f"Words: {game_data.get('totalWords', 0)}")
        print(f"Streak: {game_data.get('streak', 0)} days")
        print(f"{'='*50}\n")

        return jsonify({
            'success': True,
            'filename': filename,
            'gameData': game_data
        })

    except Exception as e:
        print(f"Error saving audio: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/submit_rating', methods=['POST'])
def submit_rating():
    try:
        data = request.json
        transcription_quality = data.get('transcription_quality', 0)
        ui = data.get('ui', 0)
        accuracy = data.get('accuracy', 0)
        timestamp = data.get('timestamp', datetime.now().isoformat())
        game_data = data.get('gameData', {})

        review = {
            'timestamp': timestamp,
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'ratings': {
                'transcription_quality': transcription_quality,
                'ui': ui,
                'accuracy': accuracy
            },
            'average': round((transcription_quality + ui + accuracy) / 3, 2),
            'gameData': game_data
        }

        review_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"review_{review_timestamp}.json"
        filepath = os.path.join(REVIEW_DIR, filename)

        with open(filepath, 'w') as f:
            json.dump(review, f, indent=4)

        print(f"\n{'=' * 50}")
        print("✨ New Review Submitted:")
        print(f"Transcription Quality: {transcription_quality}/5 ⭐")
        print(f"UI: {ui}/5 ⭐")
        print(f"Accuracy: {accuracy}/5 ⭐")
        print(f"Average: {review['average']}/5 ⭐")
        print(f"Player Level: {game_data.get('level', 1)}")
        print(f"Saved to: {filepath}")
        print(f"{'=' * 50}\n")

        return jsonify({
            'success': True,
            'filename': filename,
            'review': review
        })

    except Exception as e:
        print(f"Error saving review: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("🎮 SPEECH QUEST - Gamified Speech-to-Text with Rating System")
    print("=" * 70)
    print("\n🚀 Starting server...")
    print("🌐 Open: http://localhost:5000")
    print("\n✨ Gamification Features:")
    print("  ⭐ XP & Level System")
    print("  🏆 15 Unique Achievements")
    print("  📋 Daily Challenges")
    print("  🔥 Streak Tracking")
    print("  💎 Quality Bonuses")
    print("  ⭐ 5-Star Rating System")
    print("  🎁 +100 XP Bonus for Feedback!")
    print("  👑 Reach Level 10 to become Speech Legend!")
    print(f"\n📁 Directories:")
    print(f"  Audio: {AUDIO_DIR}")
    print(f"  Reviews: {REVIEW_DIR}")
    print(f"  Game Data: {GAME_DIR}")
    print("\n" + "=" * 70 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5000)