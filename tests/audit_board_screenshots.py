"""先预审无标签素材，再对可用样本做单帧识别；不计算准确率。"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sonar_config import get_level_config
from vision import read_image
from vision.board_debug import write_image
from vision.board_materials import assess_board_material
from vision.board_recognition import recognize_board, resolve_reference_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=PROJECT_ROOT / "runtime/screenshots/auto_probe")
    parser.add_argument("--level", type=int, default=11, help="本批素材所用几何配置，不从文件名推断关卡")
    parser.add_argument("--reference")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--recognize-limit", type=int, default=16)
    parser.add_argument("--workers", type=int, default=4, help="独立素材预审线程数；不改变单张识别规则")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or PROJECT_ROOT / "outputs/material_audit" / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    output.mkdir(parents=True, exist_ok=False)
    level = get_level_config(args.level)
    reference_path = resolve_reference_path(args.level, args.reference)
    reference = read_image(reference_path)
    paths = sorted(path for path in args.directory.iterdir() if path.suffix.lower() in {".png", ".jpg", ".jpeg"})
    if args.limit:
        paths = paths[:args.limit]
    rows, usable = [], []
    def inspect(path):
        try:
            quality = assess_board_material(reference, read_image(path), level)
            return {"path": str(path.resolve()), **asdict(quality)}
        except (OSError, ValueError, RuntimeError) as exc:
            return {"path": str(path.resolve()), "category": "unusable",
                    "suitable_for_tuning": False, "reasons": [str(exc)]}

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool, \
            (output / "quality.jsonl").open("w", encoding="utf-8") as stream:
        for index, row in enumerate(pool.map(inspect, paths)):
            if row["suitable_for_tuning"]:
                usable.append(Path(row["path"]))
            rows.append(row)
            stream.write(json.dumps(row, ensure_ascii=False)+"\n")
            stream.flush()
            if (index+1) % 50 == 0:
                print(f"quality {index+1}/{len(paths)}", flush=True)
    # 均匀取样，避免只看一轮开局。识别阶段明确晚于全量素材预审。
    import numpy as np
    selected = [usable[i] for i in np.unique(np.linspace(0, len(usable)-1,
                 min(args.recognize_limit, len(usable)), dtype=int))] if usable and args.recognize_limit else []
    recognized = []
    for index, path in enumerate(selected):
        result = recognize_board(reference, read_image(path), level_config=level,
                                  output_dir=output / "recognition" / path.stem)
        recognized.append({"path": str(path.resolve()), "counts": result.counts,
                           "review_count": len(result.review_cells), "quality": result.quality,
                           "sunk_submarines": [asdict(ship) for ship in result.sunk_submarines],
                           "issues": result.issues})
        print(f"recognize {index+1}/{len(selected)} {result.counts} review={len(result.review_cells)}", flush=True)
    summary = {"reference": str(reference_path.resolve()), "assumed_level": args.level,
               "total": len(rows), "categories": dict(Counter(row["category"] for row in rows)),
               "recognized": recognized,
               "limitation": "素材无人工标签，质量类别为自动启发式预审；未计算识别准确率。关卡几何由命令行指定。"}
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    # 为每个质量类别生成有文件名的缩略图，便于人工抽查。
    import cv2
    for category in sorted({row["category"] for row in rows}):
        group = [row for row in rows if row["category"] == category]
        sample = [group[i] for i in np.unique(np.linspace(0, len(group)-1, min(12, len(group)), dtype=int))]
        canvas = np.zeros((len(sample)//3*210 + (210 if len(sample)%3 else 0), 960, 3), np.uint8)
        for i, row in enumerate(sample):
            try:
                thumb = cv2.resize(read_image(row["path"]), (320, 180))
            except (OSError, RuntimeError):
                continue
            x, y = i%3*320, i//3*210
            canvas[y:y+180, x:x+320] = thumb
            cv2.putText(canvas, Path(row["path"]).stem[-35:], (x+3, y+197),
                        cv2.FONT_HERSHEY_SIMPLEX, .29, (255, 255, 255), 1)
        write_image(output / f"contact_{category}.png", canvas)
    print(json.dumps({"output": str(output), "total": summary["total"], "categories": summary["categories"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
