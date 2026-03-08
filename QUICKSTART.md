# QUICK START GUIDE

## Prerequisites
- Python 3.9+
- Node.js 16+
- MongoDB
- FFmpeg
- OpenAI API Key

## Installation (5 minutes)

### 1. Configure Environment
```bash
cd backend
cp .env.template .env
```

Edit `.env` and add your OpenAI API key:
```
OPENAI_API_KEY=sk-your-key-here
```

### 2. Install Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Install Frontend
```bash
cd frontend
npm install
```

### 4. Start MongoDB
```bash
# Using Docker (recommended)
docker run -d -p 27017:27017 --name mongodb mongo:latest

# OR install locally from mongodb.com
```

### 5. Test RTSP Connection
```bash
cd backend
python -m services.frame_capture
```

If connection fails, verify:
- Camera IP: ping 192.168.1.3
- Login: try rtsp://admin:admin123@192.168.1.3:554/Streaming/Channels/201 in VLC
- Firewall: check port 554 is open

### 6. Run the System

**Terminal 1 - Backend API:**
```bash
cd backend
python -m api.main
```

**Terminal 2 - Event Processor:**
```bash
cd backend  
python -m services.event_processor
```

**Terminal 3 - Frontend:**
```bash
cd frontend
npm run dev
```

### 7. Access Dashboard
Open http://localhost:5173

## Quick Actions

### Generate Daily Summary
```bash
cd backend
python -m services.summarizer
```

### Test Detection
```bash
cd backend
python -m services.detection
```

### Query Events
In the dashboard, go to "Ask Claude" tab and try:
- "Show me people detected after 5 PM"
- "What happened this morning?"
- "Were there any cars today?"

## Troubleshooting

### No events showing
1. Check event processor is running
2. Verify RTSP connection
3. Check logs: `tail -f backend/logs/app.log`

### Summary not generating  
1. Verify OpenAI API key is set
2. Check you have events for the day
3. Try manual generation in Daily Summary tab

### Video clips not playing
1. Check storage/clips directory exists
2. Verify FFmpeg is installed
3. Check clip file exists

## Docker Quick Start

```bash
# Copy environment file
cp .env.example .env

# Edit .env and add OpenAI key

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

Access at http://localhost:5173

## Default Configuration

- **RTSP URL**: rtsp://admin:admin123@192.168.1.3:554/Streaming/Channels/201
- **Frame Skip**: Process every 5th frame
- **Detection Confidence**: 50%
- **Event Cooldown**: 30 seconds
- **Clip Duration**: 10 seconds (3s before + 7s after)

## Next Steps

1. **Adjust Detection Settings**: Edit `backend/.env`
   - Lower `DETECTION_CONFIDENCE` for more detections
   - Increase `FRAME_SKIP` to reduce CPU usage

2. **Add More Cameras**: Edit `backend/config/settings.py`

3. **Schedule Daily Summaries**: The system auto-generates at 23:59

4. **Enable GPU**: Install CUDA and set `YOLO_DEVICE=cuda`

## Support

- Check README.md for full documentation
- Review logs in `backend/logs/app.log`
- Test individual components (see README)
