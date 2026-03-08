import cv2
import logging
import time
from datetime import datetime
from queue import Queue
from threading import Thread, Event
from config.settings import settings
import numpy as np
import os

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

class FrameCaptureService:
    """Service to capture frames from RTSP stream"""
    
    def __init__(self, rtsp_url: str = None, frame_queue: Queue = None):
        self.rtsp_url = rtsp_url or settings.RTSP_URL
        self.frame_queue = frame_queue or Queue(maxsize=getattr(settings, 'FRAME_QUEUE_MAXSIZE', 10))
        cv2.setNumThreads(1)
        self.stop_event = Event()
        self.capture = None
        self.thread = None
        self.frame_count = 0
        self.reconnect_delay = 5  # seconds
        
    def start(self):
        """Start the frame capture thread"""
        logger.info(f"Starting frame capture from {self.rtsp_url}")
        self.stop_event.clear()
        self.thread = Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        logger.info("Frame capture thread started")
    
    def stop(self):
        """Stop the frame capture thread"""
        logger.info("Stopping frame capture...")
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)
        if self.capture:
            self.capture.release()
        logger.info("Frame capture stopped")
    
    def _connect_to_stream(self):
        """Connect to RTSP stream with retry logic"""
        logger.info("Attempting to connect to RTSP stream...")
        
        # Release existing capture if any
        if self.capture:
            self.capture.release()
        
        # Configure FFmpeg capture options
        opts = []
        try:
            if getattr(settings, 'RTSP_FORCE_TCP', True):
                opts.append('rtsp_transport;tcp')
            opts.append(f"stimeout;{getattr(settings, 'RTSP_STIMEOUT_MS', 3000000)}")
            opts.append(f"max_delay;{getattr(settings, 'RTSP_MAX_DELAY_US', 500000)}")
            opts.append('reorder_queue_size;0')
            os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = '|'.join(opts)
        except Exception:
            pass
        
        # OpenCV VideoCapture with RTSP
        self.capture = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
        
        # Set buffer size to reduce latency
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 3)
        
        # Set resolution if configured
        cw = getattr(settings, 'CAPTURE_WIDTH', 0)
        ch = getattr(settings, 'CAPTURE_HEIGHT', 0)
        if cw and ch:
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, int(cw))
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, int(ch))
        
        if not self.capture.isOpened():
            logger.error("Failed to open RTSP stream")
            return False
        
        logger.info("Successfully connected to RTSP stream")
        
        # Get stream properties
        fps = self.capture.get(cv2.CAP_PROP_FPS)
        width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        logger.info(f"Stream properties - FPS: {fps}, Resolution: {width}x{height}")
        
        return True
    
    def _capture_loop(self):
        """Main capture loop"""
        consecutive_failures = 0
        max_failures = 10
        
        while not self.stop_event.is_set():
            try:
                # Connect to stream if not connected
                if not self.capture or not self.capture.isOpened():
                    if not self._connect_to_stream():
                        logger.warning(f"Connection failed. Retrying in {self.reconnect_delay}s...")
                        time.sleep(self.reconnect_delay)
                        continue
                
                # Read frame
                ret, frame = self.capture.read()
                
                if not ret or frame is None:
                    consecutive_failures += 1
                    logger.warning(f"Failed to read frame (attempt {consecutive_failures}/{max_failures})")
                    
                    if consecutive_failures >= max_failures:
                        logger.error("Too many consecutive failures. Reconnecting...")
                        consecutive_failures = 0
                        self.capture.release()
                        time.sleep(self.reconnect_delay)
                        continue
                    
                    time.sleep(0.1)
                    continue
                
                # Reset failure counter on success
                consecutive_failures = 0
                self.frame_count += 1
                
                # Skip frames based on FRAME_SKIP setting
                if self.frame_count % settings.FRAME_SKIP != 0:
                    continue
                
                # Add timestamp to frame metadata
                frame_data = {
                    'frame': frame,
                    'timestamp': datetime.utcnow(),
                    'frame_number': self.frame_count
                }
                
                # Add to queue (non-blocking)
                if not self.frame_queue.full():
                    self.frame_queue.put(frame_data)
                else:
                    # Remove old frame and add new one
                    try:
                        self.frame_queue.get_nowait()
                    except:
                        pass
                    self.frame_queue.put(frame_data)
                
                # Small delay to prevent CPU overload
                time.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Error in capture loop: {e}")
                time.sleep(1)
        
        logger.info("Capture loop ended")
    
    def get_frame(self, timeout=1):
        """Get a frame from the queue"""
        try:
            return self.frame_queue.get(timeout=timeout)
        except:
            return None
    
    def is_alive(self):
        """Check if capture thread is alive"""
        return self.thread and self.thread.is_alive()


def test_rtsp_connection():
    """Test RTSP connection"""
    logger.info("Testing RTSP connection...")
    logger.info(f"RTSP URL: {settings.RTSP_URL}")
    
    cap = cv2.VideoCapture(settings.RTSP_URL, cv2.CAP_FFMPEG)
    
    if not cap.isOpened():
        logger.error("❌ Failed to connect to RTSP stream")
        logger.error("Please check:")
        logger.error("  1. Camera IP address is correct")
        logger.error("  2. Username and password are correct")
        logger.error("  3. Camera is on the same network")
        logger.error("  4. Stream path is correct")
        return False
    
    logger.info("✅ Successfully connected to RTSP stream")
    
    # Try to read a frame
    ret, frame = cap.read()
    if ret and frame is not None:
        logger.info(f"✅ Successfully captured frame: {frame.shape}")
        # Save test image
        cv2.imwrite("test_frame.jpg", frame)
        logger.info("Test frame saved as test_frame.jpg")
    else:
        logger.error("❌ Failed to read frame from stream")
        cap.release()
        return False
    
    cap.release()
    logger.info("Connection test completed successfully")
    return True


if __name__ == "__main__":
    # Test mode
    print("=" * 60)
    print("RTSP Connection Test")
    print("=" * 60)
    
    # Test connection
    if test_rtsp_connection():
        print("\n" + "=" * 60)
        print("Starting live capture test (10 seconds)...")
        print("=" * 60)
        
        # Start capture service
        service = FrameCaptureService()
        service.start()
        
        # Capture for 10 seconds
        start_time = time.time()
        frame_count = 0
        
        while time.time() - start_time < 10:
            frame_data = service.get_frame()
            if frame_data:
                frame_count += 1
                print(f"Captured frame {frame_count} at {frame_data['timestamp']}")
        
        service.stop()
        print(f"\n✅ Successfully captured {frame_count} frames in 10 seconds")
    else:
        print("\n❌ Connection test failed")
