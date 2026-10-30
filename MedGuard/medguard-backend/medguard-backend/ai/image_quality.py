"""Classical, explainable quality checks used before safety decisions."""

import numpy as np


def check_image_quality(image_path: str) -> dict:
    try:
        import cv2
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError("not an image")
        height, width = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur, brightness, contrast = float(cv2.Laplacian(gray, cv2.CV_64F).var()), float(gray.mean()), float(gray.std())
        glare_ratio = float(np.mean(gray >= 245))
        reasons = []
        if min(width, height) < 640: reasons.append("image_resolution_too_low")
        if blur < 85: reasons.append("image_is_blurry")
        if brightness < 45: reasons.append("image_is_too_dark")
        if brightness > 220: reasons.append("image_is_overexposed")
        if contrast < 22: reasons.append("low_text_contrast_or_faded_packaging")
        if glare_ratio > 0.12: reasons.append("excessive_glare")
        return {"is_acceptable": not reasons, "retake_required": bool(reasons), "reasons": reasons,
                "metrics": {"width": width, "height": height, "blur_variance": round(blur, 2), "brightness": round(brightness, 2), "contrast": round(contrast, 2), "glare_ratio": round(glare_ratio, 3)}}
    except Exception:
        return {"is_acceptable": False, "retake_required": True, "reasons": ["image_could_not_be_analyzed"], "metrics": {}}
