"""全局识别 debug 图和 JSON；与识别算法、正式 GUI 隔离。"""
from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

import cv2
import numpy as np

from .board_alignment import project


COLORS = {"unknown": (190, 190, 190), "miss": (235, 150, 45),
          "hit": (0, 160, 255), "sunk": (70, 220, 70)}
SYMBOLS = {"unknown": "U", "miss": "M", "hit": "H", "sunk": "S"}


def write_image(path: Path, image):
    ok, data = cv2.imencode(path.suffix, image)
    if not ok:
        raise RuntimeError(f"debug图片编码失败：{path}")
    data.tofile(str(path))


def save_board_debug(result, images, cfg, output_dir):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    # 同一目录禁止覆盖上一轮结果。
    if any(output.iterdir()):
        raise FileExistsError(f"输出目录已有结果，请使用新目录：{output}")
    overlay = images.aligned.copy()
    rect_overlay = images.rectified.copy()
    inverse = np.linalg.inv(images.reference_to_rectified)
    side, pad = cfg.cell_pixels, images.padding
    for cell in result.cells:
        x, y = pad+cell.col*side, pad+cell.row*side
        poly = np.float32([[x, y], [x+side, y], [x+side, y+side], [x, y+side]])
        color = COLORS[cell.state.value]
        if cell.needs_review:
            color = (50, 40, 255)
        cv2.polylines(overlay, [np.int32(project(poly, inverse))], True, color, 1)
        center = project([[x+side/2, y+side/2]], inverse)[0].astype(int)
        label = f"{cell.row+1},{cell.col+1} {SYMBOLS[cell.state.value]}"
        cv2.putText(overlay, label, tuple(center-[20, 2]), cv2.FONT_HERSHEY_SIMPLEX, 0.28, color, 1, cv2.LINE_AA)
        cv2.putText(overlay, f"{cell.confidence:.2f}" + ("!" if cell.needs_review else ""), tuple(center+[0, 10]),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.27, color, 1, cv2.LINE_AA)
        cv2.rectangle(rect_overlay, (x, y), (x+side, y+side), color, 1)
        cv2.putText(rect_overlay, label, (x+3, y+20), cv2.FONT_HERSHEY_SIMPLEX, 0.34, color, 1)
        cv2.putText(rect_overlay, f"{cell.confidence:.2f}" + ("!" if cell.needs_review else ""), (x+3, y+40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.34, color, 1)
    for ship in result.sunk_submarines:
        r0, c0 = min(ship.cells)
        r1, c1 = max(ship.cells)
        poly = np.float32([[pad+c0*side, pad+r0*side], [pad+(c1+1)*side, pad+r0*side],
                          [pad+(c1+1)*side, pad+(r1+1)*side], [pad+c0*side, pad+(r1+1)*side]])
        cv2.polylines(overlay, [np.int32(project(poly, inverse))], True, COLORS["sunk"], 3)
        cv2.polylines(rect_overlay, [np.int32(poly)], True, COLORS["sunk"], 3)
    items = {"original": images.original, "aligned": images.aligned,
             "reference": images.reference, "overlay": overlay,
             "rectified_overlay": rect_overlay, "rectified": images.rectified,
             "rectified_reference": images.rectified_reference,
             "difference": np.uint8(np.clip(images.difference*3, 0, 255)),
             "ship_mask": np.uint8(images.ship_mask*255),
             "occlusion_mask": images.occlusion_mask}
    paths = {}
    for name, image in items.items():
        path = output / f"{name}.png"
        write_image(path, image)
        paths[name] = str(path.resolve())
    paths["result"] = str((output / "result.json").resolve())
    payload = asdict(result)
    payload["debug_paths"] = paths
    payload["config"] = asdict(cfg)
    (output / "result.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return paths
