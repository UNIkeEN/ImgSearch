import json
import math
from pathlib import Path
from uuid import uuid4

import numpy as np


def save_json_vector(vector: list[float]) -> str:
    return json.dumps(vector, ensure_ascii=True)


def load_json_vector(value: str | None) -> list[float] | None:
    if not value:
        return None
    return json.loads(value)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    left_array = np.asarray(left, dtype=float)
    right_array = np.asarray(right, dtype=float)
    left_norm = np.linalg.norm(left_array)
    right_norm = np.linalg.norm(right_array)
    if math.isclose(left_norm, 0.0) or math.isclose(right_norm, 0.0):
        return 0.0
    return float(np.dot(left_array, right_array) / (left_norm * right_norm))


def build_storage_path(base_dir: Path, original_filename: str) -> Path:
    target_dir = base_dir / uuid4().hex
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / original_filename
