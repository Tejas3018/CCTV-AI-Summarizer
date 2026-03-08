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
RTSP_URL=rtsp://admin:admin123@192.168.1.3:554/Streaming/Channels/201
CAMERA_NAME=Home_Camera

# MongoDB
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=cctv_ai

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

### 5. Setup MongoDB

**Option A: Using Docker**
```bash
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

**Option B: Local Installation**
- Download from: https://www.mongodb.com/try/download/community
- Install and start the service

### 6. Install Frontend Dependencies

```bash
cd frontend
npm install
```

### 7. Create Storage Directories

```bash
mkdir -p storage/clips storage/thumbnails
```

## Running the Application

### Option 1: Using Docker Compose (Recommended)

```bash
docker-compose up -d
```

### Option 2: Manual Start

**Terminal 1 - MongoDB (if not using Docker):**
```bash
mongod
```

**Terminal 2 - Backend Services:**
```bash
cd backend
python -m services.frame_capture &
python -m services.event_processor &
python -m services.summarizer &
python -m api.main
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

## RTSP Camera Connection

### Your Camera Configuration
```
URL: rtsp://admin:admin123@192.168.1.3:554/Streaming/Channels/201
Username: admin
Password: admin123
IP: 192.168.1.3
Port: 554
Stream Path: /Streaming/Channels/201
```

### Testing RTSP Connection

```bash
# Using FFmpeg
ffmpeg -rtsp_transport tcp -i rtsp://admin:admin123@192.168.1.3:554/Streaming/Channels/201 -frames:v 1 test.jpg

# Using VLC
vlc rtsp://admin:admin123@192.168.1.3:554/Streaming/Channels/201
```

### Troubleshooting RTSP

1. **Connection Timeout**
   - Check camera is on same network
   - Verify IP address: `ping 192.168.1.3`
   - Check firewall settings

2. **Authentication Failed**
   - Verify username/password in camera settings
   - Try accessing via browser: `http://192.168.1.3`

3. **Stream Not Available**
   - Check stream path in camera settings
   - Try main stream: `/Streaming/Channels/101`
   - Try sub stream: `/Streaming/Channels/201`

## Database Schema

### Events Collection
```javascript
{
  _id: ObjectId,
  timestamp: DateTime,
  camera_id: String,
  detection_type: String,  // "person", "car", "dog", etc.
  confidence: Float,
  bounding_box: {
    x: Int,
    y: Int,
    width: Int,
    height: Int
  },
  clip_path: String,
  thumbnail_path: String,
  metadata: {
    duration: Float,
    frame_count: Int
  }
}
```

### Daily Summaries Collection
```javascript
{
  _id: ObjectId,
  date: Date,
  summary: String,
  events_count: Int,
  key_events: Array,
  statistics: {
    total_detections: Int,
    by_type: Object,
    peak_hours: Array
  }
}
```

## Advanced Configuration

### GPU Acceleration (CUDA)

Install CUDA-enabled PyTorch:
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

Update `backend/services/detection.py`:
```python
device = 'cuda' if torch.cuda.is_available() else 'cpu'
```

### Multiple Cameras

Add cameras in `backend/config/settings.py`:
```python
CAMERAS = [
    {
        "id": "camera_1",
        "name": "Front Door",
        "rtsp_url": "rtsp://admin:admin123@192.168.1.3:554/Streaming/Channels/201"
    },
    {
        "id": "camera_2",
        "name": "Backyard",
        "rtsp_url": "rtsp://admin:admin123@192.168.1.4:554/Streaming/Channels/201"
    }
]
```

### Custom Detection Classes

Modify `backend/services/detection.py`:
```python
# Filter specific classes
DETECTION_CLASSES = [0, 2, 5, 7]  # person, car, bus, truck
```

## API Endpoints

### Events
- `GET /api/events` - List all events
- `GET /api/events/{event_id}` - Get specific event
- `GET /api/events/today` - Today's events
- `GET /api/events/range?start=...&end=...` - Events in time range

### Summaries
- `GET /api/summary/today` - Today's summary
- `POST /api/summary/generate` - Generate new summary
- `GET /api/summary/date/{date}` - Summary for specific date

### Query
- `POST /api/query` - Natural language query
  ```json
  {
    "query": "Show me people detected after 5 PM",
    "date": "2024-02-15"
  }
  ```

### Clips
- `GET /api/clips/{event_id}` - Stream video clip
- `GET /api/thumbnails/{event_id}` - Get thumbnail

## Performance Optimization

### 1. Frame Skip
Process every Nth frame to reduce CPU usage:
```env
FRAME_SKIP=5  # Process every 5th frame (6 FPS from 30 FPS stream)
```

### 2. Resolution
Lower resolution for faster processing:
```python
# In frame_capture.py
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
```

### 3. Detection Confidence
Higher threshold = fewer false positives:
```env
DETECTION_CONFIDENCE=0.6
```

## Troubleshooting

### High CPU Usage
- Increase `FRAME_SKIP`
- Use GPU acceleration
- Lower camera resolution

### Missing Events
- Lower `DETECTION_CONFIDENCE`
- Decrease `FRAME_SKIP`
- Check camera angle and lighting

### Storage Issues
- Implement clip retention policy
- Compress old clips
- Use external storage

## Maintenance

### Daily Tasks
- Check disk space: `df -h`
- Monitor logs: `tail -f backend/logs/app.log`

### Weekly Tasks
- Review and delete old clips
- Check MongoDB size: `db.stats()`
- Update YOLO models if available

### Backup
```bash
# Backup MongoDB
mongodump --db cctv_ai --out backup/

# Backup clips
tar -czf clips_backup.tar.gz storage/clips/
```

## Security Recommendations

1. **Change Default Credentials**
   - Update camera password
   - Use strong admin passwords

2. **Network Security**
   - Use VPN for remote access
   - Isolate camera on separate VLAN
   - Enable HTTPS for web interface

3. **API Security**
   - Implement authentication (JWT)
   - Add rate limiting
   - Use environment variables for secrets

## License

MIT License - See LICENSE file

## Support

For issues or questions:
- Check documentation
- Review logs in `backend/logs/`
- Open GitHub issue

## Credits

- YOLOv8 by Ultralytics
- OpenAI GPT API
- FastAPI Framework
- React + Vite
