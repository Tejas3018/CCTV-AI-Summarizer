# AI-Based CCTV Summarizer System

Complete AI-powered CCTV monitoring system with YOLO detection, daily summaries, and interactive querying.

## System Architecture

```
CCTV Camera (RTSP)
    ↓
Frame Capture Service
    ↓
Human/Event Detection (YOLO)
    ↓
Event Storage (MongoDB + Video Clips)
    ↓
Daily Summarizer (OpenAI GPT)
    ↓
Query Engine (OpenAI + RAG)
    ↓
Dashboard (React) / API (FastAPI)
```

## Features

- ✅ Real-time RTSP stream processing
- ✅ YOLO-based human and object detection
- ✅ Automatic event detection and clip extraction
- ✅ Daily AI-generated summaries
- ✅ Natural language queries about footage
- ✅ Timeline-based clip viewing
- ✅ Web dashboard for monitoring

## Project Structure

```
cctv-ai-summarizer/
├── backend/
│   ├── services/
│   │   ├── frame_capture.py      # RTSP stream capture
│   │   ├── detection.py          # YOLO detection service
│   │   ├── event_processor.py    # Event detection & clip extraction
│   │   ├── summarizer.py         # Daily summary generation
│   │   └── query_engine.py       # OpenAI query handler
│   ├── api/
│   │   ├── main.py               # FastAPI application
│   │   └── routes/
│   │       ├── events.py
│   │       ├── summary.py
│   │       └── query.py
│   ├── models/
│   │   └── database.py           # MongoDB models
│   ├── config/
│   │   └── settings.py           # Configuration
│   └── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Timeline.jsx
│   │   │   ├── ChatInterface.jsx
│   │   │   └── VideoPlayer.jsx
│   │   ├── App.jsx
│   │   └── main.jsx
│   └── package.json
├── storage/
│   ├── clips/                    # Video clips
│   └── thumbnails/               # Event thumbnails
├── docker-compose.yml
└── README.md
```

## Prerequisites

- Python 3.9+
- Node.js 16+
- MongoDB
- FFmpeg
- CUDA (optional, for GPU acceleration)
- OpenAI API Key

## Installation Steps

### 1. Clone and Setup Environment

```bash
cd cctv-ai-summarizer
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Download YOLO Weights

```bash
# YOLOv8 will auto-download on first run, or manually:
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt -P models/
```

### 4. Configure Environment Variables

Create `backend/.env` file:

```env
# RTSP Camera Configuration
RTSP_URL=YOUR RTSP URL
CAMERA_NAME=Home_Camera

# MongoDB
MONGODB_URL=
DATABASE_NAME=

# OpenAI
OPENAI_API_KEY=your_openai_api_key_here

# Storage
CLIPS_STORAGE_PATH=../storage/clips
THUMBNAILS_PATH=../storage/thumbnails

# Detection Settings
DETECTION_CONFIDENCE=0.5
FRAME_SKIP=5  # Process every 5th frame
EVENT_COOLDOWN=30  # seconds between same events

# API
API_HOST=0.0.0.0
API_PORT=8000
```


### 5. Install Frontend Dependencies

```bash
cd frontend
npm install
```

### 6. Create Storage Directories

```bash
mkdir -p storage/clips storage/thumbnails
```

## Running the Application

**Terminal 1 - Backend Services:**
```bash
cd backend
python -m api.main
```
**Terminal 2 - Backend Services:**
```bash
cd backend
python -m services.event_processor 
```

**Terminal 3 - Frontend:**
```bash
cd frontend
npm run dev
```

## Access the Application

- **Frontend Dashboard**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## Usage Guide

### 1. Monitor Live Events
- Dashboard shows real-time detections
- Events appear as they're detected

### 2. View Daily Summary
- Click "Generate Summary" to get AI summary of the day
- Summary includes key events, timestamps, and statistics

### 3. Query System
- Use natural language: "Show me when someone entered the house at 3 PM"
- "Were there any people detected between 2-4 PM?"
- "What happened around 5:30 PM today?"

### 4. Browse Timeline
- Scroll through timeline to see all events
- Click on events to view clips
- Filter by detection type (person, car, etc.)

