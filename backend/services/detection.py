from ultralytics import YOLO
from ultralytics.nn.tasks import DetectionModel
from ultralytics.nn.modules import Conv
from ultralytics.nn.modules import C2f, SPPF
from ultralytics.nn.modules import Detect
import cv2
import numpy as np
import logging
from datetime import datetime
from config.settings import settings, COCO_CLASSES
from typing import List, Dict, Tuple
import torch
from services.attributes import AgeGenderClassifier
from torch.nn import Sequential, Conv2d, BatchNorm2d, SiLU, Linear, MaxPool2d, AdaptiveAvgPool2d, Upsample, Dropout

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

class DetectionService:
    """YOLO-based object detection service"""
    
    def __init__(self):
        self.model = None
        self.device = settings.YOLO_DEVICE
        self.confidence_threshold = settings.DETECTION_CONFIDENCE
        self.target_classes = settings.DETECTION_CLASSES
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=settings.MOTION_HISTORY,
            varThreshold=settings.MOTION_VAR_THRESHOLD,
            detectShadows=True
        )
        self.morph_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (settings.MOTION_KERNEL_SIZE, settings.MOTION_KERNEL_SIZE))
        self.moving_min_ratio = settings.MOTION_MIN_AREA_RATIO
        self.prev_frame_gray = None
        self.prev_detections = []
        self.attr = AgeGenderClassifier() if getattr(settings, 'ATTRIBUTES_ENABLED', False) else None
        self._load_model()
    
    def _load_model(self):
        """Load YOLO model"""
        try:
            logger.info(f"Loading YOLO model: {settings.YOLO_MODEL}")
            logger.info(f"Using device: {self.device}")
            
            # Check CUDA availability
            if self.device == 'cuda' and not torch.cuda.is_available():
                logger.warning("CUDA requested but not available. Using CPU instead.")
                self.device = 'cpu'
            
            orig_load = torch.load
            def _patched_load(*args, **kwargs):
                kwargs.setdefault('weights_only', False)
                return orig_load(*args, **kwargs)
            torch.load = _patched_load
            try:
                self.model = YOLO(settings.YOLO_MODEL)
            finally:
                torch.load = orig_load
            
            if self.device == 'cuda':
                self.model.to('cuda')
            
            logger.info("YOLO model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            raise
    
    def detect(self, frame: np.ndarray) -> List[Dict]:
        """
        Perform object detection on a frame
        
        Returns list of detections:
        [
            {
                'class_id': int,
                'class_name': str,
                'confidence': float,
                'bbox': {'x': int, 'y': int, 'width': int, 'height': int}
            }
        ]
        """
        if self.model is None:
            logger.error("Model not loaded")
            return []
        
        try:
            # Run inference
            results = self.model(frame, conf=self.confidence_threshold, verbose=False)
            
            detections = []
            # Initialize previous state holders if missing
            if not hasattr(self, 'prev_frame_gray'):
                self.prev_frame_gray = None
            if not hasattr(self, 'prev_detections'):
                self.prev_detections = []
            
            # Prepare grayscale frame for frame-difference motion
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Helper: IoU for (x,y,w,h) boxes
            def _iou_xywh(a, b):
                ax, ay, aw, ah = a
                bx, by, bw, bh = b
                ax2, ay2 = ax + aw, ay + ah
                bx2, by2 = bx + bw, by + bh
                ix1, iy1 = max(ax, bx), max(ay, by)
                ix2, iy2 = min(ax2, bx2), min(ay2, by2)
                iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
                inter = iw * ih
                union = aw * ah + bw * bh - inter
                return (inter / union) if union > 0 else 0.0
            
            # Process results
            for result in results:
                boxes = result.boxes
                
                for box in boxes:
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    if class_id not in self.target_classes:
                        continue
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    x = int(x1)
                    y = int(y1)
                    w = int(x2 - x1)
                    h = int(y2 - y1)
                    # Background subtraction based motion
                    fgmask = self.bg_subtractor.apply(frame)
                    fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, self.morph_kernel)
                    yy1 = max(0, y)
                    yy2 = max(0, y + h)
                    xx1 = max(0, x)
                    xx2 = max(0, x + w)
                    roi = fgmask[yy1:yy2, xx1:xx2]
                    moving_ratio = float(cv2.countNonZero(roi)) / float(max(1, w * h))
                    # Frame-difference motion within ROI
                    diff_ratio = 0.0
                    if self.prev_frame_gray is not None:
                        prev_roi = self.prev_frame_gray[yy1:yy2, xx1:xx2]
                        curr_roi = gray[yy1:yy2, xx1:xx2]
                        d = cv2.absdiff(prev_roi, curr_roi)
                        _, dth = cv2.threshold(d, 25, 255, cv2.THRESH_BINARY)
                        diff_ratio = float(cv2.countNonZero(dth)) / float(max(1, w * h))
                    # Displacement of detection center vs previous detections of same class
                    disp = 0.0
                    best_iou = 0.0
                    best_prev_bbox = None
                    for pd in self.prev_detections:
                        if pd.get('class_id') != class_id:
                            continue
                        pb = pd.get('bbox', {})
                        pb_xywh = (pb.get('x', 0), pb.get('y', 0), pb.get('width', 0), pb.get('height', 0))
                        i = _iou_xywh((x, y, w, h), pb_xywh)
                        if i > best_iou:
                            best_iou = i
                            best_prev_bbox = pb_xywh
                    if best_prev_bbox is not None and best_iou > 0.3:
                        cx1 = x + w / 2.0
                        cy1 = y + h / 2.0
                        cx0 = best_prev_bbox[0] + best_prev_bbox[2] / 2.0
                        cy0 = best_prev_bbox[1] + best_prev_bbox[3] / 2.0
                        disp = ((cx1 - cx0) ** 2 + (cy1 - cy0) ** 2) ** 0.5
                    vehicle_classes = [2, 3, 5, 7]
                    # Persons (class_id == 0) and non-vehicle classes are not filtered by motion
                    if class_id in vehicle_classes:
                        disp_thresh = getattr(settings, 'MOTION_MIN_DISPLACEMENT_PIXELS', 10)
                        moving = (disp >= disp_thresh) or ((moving_ratio >= self.moving_min_ratio) and (diff_ratio >= self.moving_min_ratio))
                        if not moving:
                            continue
                    detection = {
                        'class_id': class_id,
                        'class_name': COCO_CLASSES.get(class_id, f"class_{class_id}"),
                        'confidence': confidence,
                        'bbox': {'x': x, 'y': y, 'width': w, 'height': h}
                    }
                    if class_id == 0 and self.attr is not None:
                        attr = self.attr.classify(frame, (x, y, w, h))
                        detection['attributes'] = attr
                        if attr.get('age_group') == 'kid':
                            detection['class_name'] = 'kid'
                        else:
                            g = attr.get('gender')
                            if g in ('male', 'female'):
                                detection['class_name'] = g
                    detections.append(detection)
            
            # Update previous state for next call
            self.prev_frame_gray = gray
            self.prev_detections = detections
            
            self.prev_frame_gray = gray
            self.prev_detections = detections
            return detections
            
        except Exception as e:
            logger.error(f"Detection error: {e}")
            return []
    
    def detect_and_annotate(self, frame: np.ndarray) -> Tuple[np.ndarray, List[Dict]]:
        """
        Detect objects and return annotated frame
        """
        detections = self.detect(frame)
        annotated_frame = frame.copy()
        
        for det in detections:
            bbox = det['bbox']
            x, y, w, h = bbox['x'], bbox['y'], bbox['width'], bbox['height']
            
            # Draw bounding box
            color = (0, 255, 0)  # Green
            cv2.rectangle(annotated_frame, (x, y), (x + w, y + h), color, 2)
            
            # Draw label
            label = f"{det['class_name']} {det['confidence']:.2f}"
            
            # Background for text
            (text_width, text_height), _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
            )
            cv2.rectangle(
                annotated_frame,
                (x, y - text_height - 10),
                (x + text_width, y),
                color,
                -1
            )
            
            # Text
            cv2.putText(
                annotated_frame,
                label,
                (x, y - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 0),
                2
            )
        
        return annotated_frame, detections
    
    def has_person(self, detections: List[Dict]) -> bool:
        """Check if person detected"""
        return any(d['class_id'] == 0 for d in detections)
    
    def has_vehicle(self, detections: List[Dict]) -> bool:
        """Check if vehicle detected"""
        vehicle_classes = [2, 3, 5, 7]  # car, motorcycle, bus, truck
        return any(d['class_id'] in vehicle_classes for d in detections)
    
    def get_detection_summary(self, detections: List[Dict]) -> Dict[str, int]:
        """Get count of each detected class"""
        summary = {}
        for det in detections:
            class_name = det['class_name']
            summary[class_name] = summary.get(class_name, 0) + 1
        return summary

    def _iou(self, b1: Tuple[int, int, int, int], b2: Tuple[int, int, int, int]) -> float:
        """Compute Intersection-over-Union between two boxes (x, y, width, height)."""
        x1, y1, w1, h1 = b1
        x2, y2, w2, h2 = b2
        xa = max(x1, x2)
        ya = max(y1, y2)
        xb = min(x1 + w1, x2 + w2)
        yb = min(y1 + h1, y2 + h2)
        inter_w = max(0, xb - xa)
        inter_h = max(0, yb - ya)
        inter = inter_w * inter_h
        union = w1 * h1 + w2 * h2 - inter
        return float(inter) / float(union) if union > 0 else 0.0


def test_detection():
    """Test detection on sample image or webcam"""
    logger.info("Testing YOLO detection...")
    
    detector = DetectionService()
    
    # Try to capture from webcam or create test image
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        logger.info("Webcam not available, creating test image...")
        # Create a simple test image
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(
            test_image,
            "Test Image - No webcam available",
            (50, 240),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 255, 255),
            2
        )
        frame = test_image
    else:
        ret, frame = cap.read()
        cap.release()
        if not ret:
            logger.error("Failed to capture frame")
            return
    
    logger.info("Running detection...")
    annotated_frame, detections = detector.detect_and_annotate(frame)
    
    logger.info(f"Detections found: {len(detections)}")
    for det in detections:
        logger.info(f"  - {det['class_name']}: {det['confidence']:.2f}")
    
    # Save result
    output_path = "detection_test.jpg"
    cv2.imwrite(output_path, annotated_frame)
    logger.info(f"Result saved to {output_path}")
    
    # Summary
    summary = detector.get_detection_summary(detections)
    logger.info(f"Detection summary: {summary}")


if __name__ == "__main__":
    print("=" * 60)
    print("YOLO Detection Test")
    print("=" * 60)
    test_detection()
