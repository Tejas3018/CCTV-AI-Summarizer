from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # RTSP Camera Configuration
    RTSP_URL: str = "rtsp://admin:admin123@192.168.1.2:554/Streaming/Channels/201"
    RTSP_FORCE_TCP: bool = True
    RTSP_STIMEOUT_MS: int = 3000000
    RTSP_MAX_DELAY_US: int = 500000
    CAPTURE_WIDTH: int = 1280
    CAPTURE_HEIGHT: int = 720
    CAMERA_NAME: str = "Home_Camera"
    CAMERA_ID: str = "camera_1"
    CAMERA_TIMEZONE: str = "Asia/Kolkata"
    CAMERA_TIME_OFFSET_MINUTES: int = 0
    
    # MongoDB Configuration
    MONGODB_URL: str = "mongodb+srv://tejasdruv_db_user:o45xCMOOwxI925CN@cluster0.6tgzybv.mongodb.net/?appName=Cluster0"
    DATABASE_NAME: str = "cctv_ai"
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4"
    
    # Storage Paths
    CLIPS_STORAGE_PATH: str = "../storage/clips"
    THUMBNAILS_PATH: str = "../storage/thumbnails"
    
    # Detection Settings
    DETECTION_CONFIDENCE: float = 0.5
    FRAME_SKIP: int = 8  # Process every Nth frame
    EVENT_COOLDOWN: int = 30  # Seconds between same type events
    CLIP_DURATION: int = 10  # Target seconds of video clip (used for UI/analytics)
    CLIP_BUFFER_BEFORE: int = 3  # Seconds before event
    CLIP_BUFFER_AFTER: int = 7  # Seconds after event
    CLIP_MIN_DURATION: int = 5  # Minimum seconds per event clip
    FRAME_QUEUE_MAXSIZE: int = 10
    CLIP_BUFFER_MAX_FRAMES: int = 120
    CLIP_RESIZE_WIDTH: int = 1280
    CLIP_RESIZE_HEIGHT: int = 720
    CLIP_JPEG_QUALITY: int = 80
    
    # YOLO Model
    YOLO_MODEL: str = "yolov8n.pt"  # Options: yolov8n, yolov8s, yolov8m, yolov8l, yolov8x
    YOLO_DEVICE: str = "cpu"  # 'cpu' or 'cuda'
    
    # Detection Classes (COCO dataset)
    # 0: person, 2: car, 3: motorcycle, 5: bus, 7: truck
    DETECTION_CLASSES: list = [0, 2, 3, 5, 7]
    MOTION_ENABLED: bool = True
    MOTION_HISTORY: int = 100
    MOTION_VAR_THRESHOLD: int = 16
    MOTION_MIN_AREA_RATIO: float = 0.10
    MOTION_KERNEL_SIZE: int = 3
    MOTION_MIN_DISPLACEMENT_PIXELS: int = 8
    PERSON_TRACK_TTL: int = 5
    PERSON_IOU_THRESHOLD: float = 0.5
    ATTRIBUTES_ENABLED: bool = True
    ATTRIBUTES_PROVIDER: str = "deepface"
    DEEPFACE_DETECTOR_BACKEND: str = "retinaface"
    AGE_MODEL_PROTO: str = "models/age_gender/deploy_age.prototxt"
    AGE_MODEL_WEIGHTS: str = "models/age_gender/age_net.caffemodel"
    GENDER_MODEL_PROTO: str = "models/age_gender/deploy_gender.prototxt"
    GENDER_MODEL_WEIGHTS: str = "models/age_gender/gender_net.caffemodel"
    FACE_DETECTOR: str = "haar"
    HAAR_CASCADE_FILENAME: str = "haarcascade_frontalface_default.xml"
    AGE_KID_MAX: int = 16
    
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000"]
    
    # Summarizer Settings
    SUMMARY_GENERATION_TIME: str = "23:59"  # Time to generate daily summary
    MAX_EVENTS_IN_SUMMARY: int = 50
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Singleton instance
settings = Settings()

# Ensure storage directories exist
os.makedirs(settings.CLIPS_STORAGE_PATH, exist_ok=True)
os.makedirs(settings.THUMBNAILS_PATH, exist_ok=True)
os.makedirs("logs", exist_ok=True)

# COCO class names
COCO_CLASSES = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
    15: "cat",
    16: "dog",
    24: "backpack",
    26: "handbag",
    28: "suitcase"
}