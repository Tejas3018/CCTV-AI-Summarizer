import cv2
import os
import numpy as np
import logging
from config.settings import settings

logger = logging.getLogger(__name__)

try:
    from deepface import DeepFace as _DeepFace
except Exception:
    _DeepFace = None


class AgeGenderClassifier:
    def __init__(self):
        self.kid_max_age_bucket = getattr(settings, "AGE_KID_MAX", 12)
        self.detector_backend = getattr(settings, "DEEPFACE_DETECTOR_BACKEND", "retinaface")
        self.enabled = getattr(settings, "ATTRIBUTES_ENABLED", True)
        self.deepface = _DeepFace

    def classify(self, frame, person_bbox):
        if not self.enabled or self.deepface is None or frame is None:
            return {"gender": "unknown", "age_group": "unknown"}

        x, y, w, h = person_bbox
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(frame.shape[1], x + w)
        y2 = min(frame.shape[0], y + h)
        roi = frame[y1:y2, x1:x2]
        if roi.size == 0:
            return {"gender": "unknown", "age_group": "unknown"}

        try:
            top_h = max(1, int(0.6 * roi.shape[0]))
            top = roi[0:top_h, :]
            if top.size > 0:
                midx = top.shape[1] // 2
                w2 = max(1, int(0.6 * top.shape[1]))
                x0 = max(0, midx - w2 // 2)
                img = top[:, x0:x0 + w2]
            else:
                img = roi
            if img.size == 0:
                return {"gender": "unknown", "age_group": "unknown"}
            h_img, w_img = img.shape[:2]
            if h_img < 60 or w_img < 60:
                return {"gender": "unknown", "age_group": "unknown"}
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            focus = cv2.Laplacian(gray, cv2.CV_64F).var()
            if focus < 40.0:
                return {"gender": "unknown", "age_group": "unknown"}

            analysis = self.deepface.analyze(
                img_path=img,
                actions=["age", "gender"],
                enforce_detection=False,
                detector_backend=self.detector_backend,
            )

            if isinstance(analysis, list):
                analysis = analysis[0]

            age = analysis.get("age")
            gender_scores = analysis.get("gender") if isinstance(analysis.get("gender"), dict) else None
            dom_gender = analysis.get("dominant_gender")

            gender = "unknown"
            gender_confidence = 0.0
            if gender_scores:
                male_prob = 0.0
                female_prob = 0.0
                for k, v in gender_scores.items():
                    kl = k.lower()
                    if kl.startswith("m"):
                        male_prob += float(v)
                    elif kl.startswith("w") or kl.startswith("f"):
                        female_prob += float(v)
                total = male_prob + female_prob
                if total > 0:
                    male_p = male_prob / total * 100.0
                    female_p = female_prob / total * 100.0
                    gender_confidence = max(male_p, female_p)
                    diff = abs(male_p - female_p)
                    if female_p >= 55.0 and female_p - male_p >= 3.0:
                        gender = "female"
                    elif male_p >= 70.0 and male_p - female_p >= 10.0:
                        gender = "male"
                    elif dom_gender is not None and diff <= 15.0:
                        g = str(dom_gender).lower()
                        if "woman" in g or "female" in g or g.startswith("f"):
                            gender = "female"
                        elif "man" in g or "male" in g or g.startswith("m"):
                            gender = "male"
            if gender == "unknown" and not gender_scores and dom_gender is not None:
                g = str(dom_gender).lower()
                if "woman" in g or "female" in g or g.startswith("f"):
                    gender = "female"
                elif "man" in g or "male" in g or g.startswith("m"):
                    gender = "male"

            age_group = "unknown"
            age_value = None
            if age is not None:
                try:
                    age_value = int(round(float(age)))
                    age_group = "kid" if age_value <= self.kid_max_age_bucket else "adult"
                except Exception:
                    age_value = None

            result = {"gender": gender, "age_group": age_group}
            if age_value is not None:
                result["age"] = age_value
            if gender_confidence > 0.0:
                result["gender_confidence"] = gender_confidence
            return result

        except Exception as e:
            logger.warning(f"DeepFace classification failed: {e}")
            return {"gender": "unknown", "age_group": "unknown"}