import cv2
import logging
import asyncio
import os
from datetime import datetime, timedelta
from collections import deque
from queue import Queue
from threading import Thread
from typing import Dict, List
import uuid
import time
import subprocess
import shutil
from moviepy.editor import ImageSequenceClip
import numpy as np
import time

from config.settings import settings
from services.frame_capture import FrameCaptureService
from services.detection import DetectionService
from models.database import EventModel, Database

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

class EventProcessor:
    """Process detections and create event clips"""
    
    def __init__(self):
        self.frame_capture = FrameCaptureService()
        self.detector = DetectionService()
        
        # Frame buffer for clip creation (stores encoded frames)
        buffer_size = getattr(settings, 'CLIP_BUFFER_MAX_FRAMES', 120)
        self.frame_buffer = deque(maxlen=buffer_size)
        
        # Event cooldown tracking
        self.last_event_time = {}
        
        # Recording state
        self.is_recording = {}
        self.recording_frames = {}
        
        self.running = False
        
        self.loop = asyncio.new_event_loop()
        self.loop_thread = Thread(target=self._run_event_loop, daemon=True)
    
    def _run_event_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
    
    def start(self):
        """Start event processing"""
        logger.info("Starting event processor...")
        self.running = True
        
        # Start frame capture
        self.frame_capture.start()
        
        # Start processing thread
        self.process_thread = Thread(target=self._process_loop, daemon=True)
        self.process_thread.start()
        
        logger.info("Event processor started")
    
    def stop(self):
        """Stop event processing"""
        logger.info("Stopping event processor...")
        self.running = False
        self.frame_capture.stop()
        if hasattr(self, 'process_thread'):
            self.process_thread.join(timeout=5)
        try:
            self.loop.call_soon_threadsafe(self.loop.stop)
            if hasattr(self, 'loop_thread'):
                self.loop_thread.join(timeout=5)
        except Exception:
            pass
        logger.info("Event processor stopped")
    
    def _process_loop(self):
        """Main processing loop"""
        logger.info("Processing loop started")
        
        while self.running:
            try:
                # Get frame from capture service
                frame_data = self.frame_capture.get_frame(timeout=1)
                
                if frame_data is None:
                    continue
                
                frame = frame_data['frame']
                timestamp = frame_data['timestamp']
                
                # Add to buffer (resized + JPEG-compressed)
                small = frame
                rw = getattr(settings, 'CLIP_RESIZE_WIDTH', 0)
                rh = getattr(settings, 'CLIP_RESIZE_HEIGHT', 0)
                if rw and rh:
                    try:
                        small = cv2.resize(frame, (rw, rh), interpolation=cv2.INTER_AREA)
                    except Exception:
                        small = frame
                q = getattr(settings, 'CLIP_JPEG_QUALITY', 80)
                ok, buf = cv2.imencode('.jpg', small, [cv2.IMWRITE_JPEG_QUALITY, int(q)])
                if ok:
                    self.frame_buffer.append({'jpeg': buf.tobytes(), 'timestamp': timestamp})
                
                # Run detection
                detections = self.detector.detect(frame)
                
                if not detections:
                    continue
                
                # Process each detection
                for detection in detections:
                    self._handle_detection(detection, frame, timestamp)
                
            except Exception as e:
                logger.error(f"Error in processing loop: {e}", exc_info=True)
        
        logger.info("Processing loop ended")
    
    def _handle_detection(self, detection: Dict, frame, timestamp: datetime):
        """Handle a single detection"""
        class_name = detection['class_name']
        confidence = detection['confidence']
        
        # Person deduplication using IoU and TTL
        if class_name in ('person','male','female','kid') and 'bbox' in detection:
            bbox = detection['bbox']
            tracks = getattr(self, 'person_tracks', [])
            ttl = getattr(settings, 'PERSON_TRACK_TTL', 5)
            iou_thr = getattr(settings, 'PERSON_IOU_THRESHOLD', 0.5)
            # Prune expired tracks
            tracks = [t for t in tracks if (timestamp - t['last_seen']).total_seconds() <= ttl]
            
            def _iou(b1, b2):
                xa = max(b1.get('x', 0), b2.get('x', 0))
                ya = max(b1.get('y', 0), b2.get('y', 0))
                xb = min(b1.get('x', 0) + b1.get('width', 0), b2.get('x', 0) + b2.get('width', 0))
                yb = min(b1.get('y', 0) + b1.get('height', 0), b2.get('y', 0) + b2.get('height', 0))
                inter_w = max(0, xb - xa)
                inter_h = max(0, yb - ya)
                inter = inter_w * inter_h
                union = b1.get('width', 0) * b1.get('height', 0) + b2.get('width', 0) * b2.get('height', 0) - inter
                return inter / union if union > 0 else 0.0
            
            dedup_hit = False
            for t in tracks:
                if _iou(bbox, t['bbox']) >= iou_thr:
                    # Same person still in frame; update last_seen and skip event
                    t['last_seen'] = timestamp
                    dedup_hit = True
                    break
            
            if dedup_hit:
                self.person_tracks = tracks
                return
            else:
                tracks.append({'bbox': bbox, 'last_seen': timestamp})
                self.person_tracks = tracks
        
        # Check cooldown
        if not self._check_cooldown(class_name, timestamp):
            return
        
        logger.info(f"Event detected: {class_name} (confidence: {confidence:.2f})")
        
        # Update last event time
        self.last_event_time[class_name] = timestamp
        
        # Create event asynchronously
        asyncio.run_coroutine_threadsafe(
            self._create_event(detection, frame, timestamp),
            self.loop
        )
    
    def _check_cooldown(self, class_name: str, current_time: datetime) -> bool:
        """Check if enough time has passed since last event of this type"""
        if class_name not in self.last_event_time:
            return True
        
        last_time = self.last_event_time[class_name]
        time_diff = (current_time - last_time).total_seconds()
        
        return time_diff >= settings.EVENT_COOLDOWN
    
    async def _create_event(self, detection: Dict, current_frame, timestamp: datetime):
        """Create event with clip and thumbnail"""
        try:
            event_id = str(uuid.uuid4())
            
            # Generate clip
            clip_path = await self._create_clip(event_id, timestamp)
            
            # Generate thumbnail
            thumbnail_path = self._create_thumbnail(event_id, current_frame, detection)
            
            # Save to database
            await EventModel.create(
                timestamp=timestamp,
                camera_id=settings.CAMERA_ID,
                detection_type=detection['class_name'],
                confidence=detection['confidence'],
                bounding_box=detection['bbox'],
                clip_path=clip_path,
                thumbnail_path=thumbnail_path,
                metadata={
                    'event_id': event_id,
                    'class_id': detection['class_id'],
                    'attributes': detection.get('attributes', {})
                }
            )
            
            logger.info(f"Event created successfully: {event_id}")
            
        except Exception as e:
            logger.error(f"Failed to create event: {e}", exc_info=True)
    
    async def _create_clip(self, event_id: str, event_time: datetime) -> str:
        """Create video clip from buffered frames"""
        try:
            # Calculate time range
            start_time = event_time - timedelta(seconds=settings.CLIP_BUFFER_BEFORE)
            end_time = event_time + timedelta(seconds=settings.CLIP_BUFFER_AFTER)
            
            # Wait briefly for post-event frames to arrive
            wait_deadline = datetime.utcnow() + timedelta(seconds=settings.CLIP_BUFFER_AFTER + 2)
            while self.frame_buffer and self.frame_buffer[-1]['timestamp'] < end_time and datetime.utcnow() < wait_deadline:
                time.sleep(0.05)
            
            clip_frames = [
                f for f in list(self.frame_buffer)
                if start_time <= f['timestamp'] <= end_time
            ]
            
            if not clip_frames:
                logger.warning("No frames available for clip")
                return ""
            
            clip_filename = f"{event_id}.mp4"
            clip_path = os.path.abspath(os.path.join(settings.CLIPS_STORAGE_PATH, clip_filename))
            
            first = cv2.imdecode(np.frombuffer(clip_frames[0]['jpeg'], dtype=np.uint8), cv2.IMREAD_COLOR)
            height, width = first.shape[:2]
            rgb_frames = [
                cv2.cvtColor(
                    cv2.imdecode(np.frombuffer(f['jpeg'], dtype=np.uint8), cv2.IMREAD_COLOR),
                    cv2.COLOR_BGR2RGB
                ) for f in clip_frames
            ]
            actual_duration = max(0.001, (clip_frames[-1]['timestamp'] - clip_frames[0]['timestamp']).total_seconds())
            min_duration = float(getattr(settings, 'CLIP_MIN_DURATION', 5))
            duration = max(min_duration, actual_duration)
            fps = max(5, min(30, int(round(len(clip_frames) / duration))))
            try:
                clip = ImageSequenceClip(rgb_frames, fps=fps)
                clip.write_videofile(
                    clip_path,
                    codec='libx264',
                    audio=False,
                    preset='ultrafast',
                    threads=2,
                    ffmpeg_params=['-movflags','+faststart']
                )
            except Exception as e:
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(clip_path, fourcc, fps, (width, height))
                for frame_data in clip_frames:
                    img = cv2.imdecode(np.frombuffer(frame_data['jpeg'], dtype=np.uint8), cv2.IMREAD_COLOR)
                    out.write(img)
                min_frames = int(fps * duration)
                if len(clip_frames) < min_frames:
                    last = cv2.imdecode(np.frombuffer(clip_frames[-1]['jpeg'], dtype=np.uint8), cv2.IMREAD_COLOR)
                    for _ in range(min_frames - len(clip_frames)):
                        out.write(last)
                out.release()
            
            logger.info(f"Clip created: {clip_path} ({len(clip_frames)} frames)")
            return clip_filename
            
        except Exception as e:
            logger.error(f"Failed to create clip: {e}")
            return ""
    
    def _create_thumbnail(self, event_id: str, frame, detection: Dict) -> str:
        """Create thumbnail with bounding box"""
        try:
            # Draw bounding box
            bbox = detection['bbox']
            x, y, w, h = bbox['x'], bbox['y'], bbox['width'], bbox['height']
            
            thumbnail = frame.copy()
            
            # Draw rectangle
            cv2.rectangle(thumbnail, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # Draw label
            label = f"{detection['class_name']} {detection['confidence']:.2f}"
            cv2.putText(
                thumbnail,
                label,
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2
            )
            
            # Save thumbnail
            thumbnail_filename = f"{event_id}.jpg"
            thumbnail_path = os.path.join(settings.THUMBNAILS_PATH, thumbnail_filename)
            cv2.imwrite(thumbnail_path, thumbnail)
            
            logger.info(f"Thumbnail created: {thumbnail_path}")
            return thumbnail_filename
            
        except Exception as e:
            logger.error(f"Failed to create thumbnail: {e}")
            return ""


def main():
    """Main entry point for event processor service"""
    logger.info("=" * 60)
    logger.info("CCTV Event Processor Service")
    logger.info("=" * 60)
    
    # Initialize processor
    processor = EventProcessor()
    
    # Start event loop thread
    processor.loop_thread.start()
    
    # Connect to database on processor loop
    try:
        fut = asyncio.run_coroutine_threadsafe(Database.connect_db(), processor.loop)
        fut.result()
        logger.info("Database connected")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}", exc_info=True)
    
    try:
        # Start processing
        processor.start()
        
        logger.info("Event processor running. Press Ctrl+C to stop.")
        
        # Keep running
        while True:
            import time
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    finally:
        try:
            fut = asyncio.run_coroutine_threadsafe(Database.close_db(), processor.loop)
            fut.result(timeout=5)
            logger.info("Database connection closed")
        except Exception:
            pass
        processor.stop()
        logger.info("Event processor shutdown complete")


if __name__ == "__main__":
    main()
