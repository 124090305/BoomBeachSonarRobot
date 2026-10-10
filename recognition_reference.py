"""只读识别参考；不持有棋盘、策略或设备控制器。"""
import cv2
from dataclasses import dataclass, field, asdict
from math import isfinite
from vision.image_match import find_template_with_score

@dataclass(frozen=True)
class RecognitionReference:
    value: str
    metric: str = "相似度"
    score: float | None = None
    threshold: float | None = None
    point: tuple | None = None
    details: dict = field(default_factory=dict)

    def to_record(self):
        def clean(v):
            if isinstance(v, float):
                return v if isfinite(v) else None
            if isinstance(v, dict):
                return {k: clean(x) for k, x in v.items()}
            if isinstance(v, (list, tuple)):
                return [clean(x) for x in v]
            return v
        return clean(asdict(self))

def template_reference(image, templates, threshold, *, matcher=find_template_with_score):
    measurements = []
    best = None
    for name in templates:
        try:
            match, score = matcher(image, name, threshold=threshold)
        except (ValueError, cv2.error) as exc:
            return RecognitionReference("unavailable", details={"error": str(exc)})
        measurements.append({"template": str(name), "score": score, "threshold": threshold})
        if best is None or score > best:
            best = score
        if match is not None:
            return RecognitionReference("found", score=score, threshold=threshold,
                                        point=match.center, details={"templates": measurements})
    return RecognitionReference("missing", score=best, threshold=threshold,
                                details={"templates": measurements})

def probe_reference(result, config=None):
    details = asdict(result)
    if config is not None:
        details["config"] = asdict(config)
    return RecognitionReference(result.state, "置信度", result.confidence,
                                details=details)
