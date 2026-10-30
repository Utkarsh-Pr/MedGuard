"""Audit raw folders and build group-safe train/validation/test manifests."""
import csv
import hashlib
import json
import os
import random
import stat
import sys
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
FIELDNAMES = ["path", "label", "source_filename", "capture_group"]


def capture_group(label, filename):
    return f"{label}/{filename.split('.rf.', 1)[0]}"


def content_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit_raw_dataset(raw_dir):
    rows, invalid, hashes = [], [], defaultdict(list)
    for class_dir in sorted((path for path in raw_dir.iterdir() if path.is_dir()), key=lambda path: path.name.lower()):
        for image_path in sorted(class_dir.iterdir()):
            if not image_path.is_file() or image_path.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            try:
                with Image.open(image_path) as image:
                    image.verify()
            except Exception as error:
                invalid.append({"path": str(image_path.resolve()), "error": str(error)})
                continue
            hashes[content_hash(image_path)].append(str(image_path.resolve()))
            rows.append({"path": str(image_path.resolve()), "label": class_dir.name,
                         "source_filename": image_path.name,
                         "capture_group": capture_group(class_dir.name, image_path.name)})
    audit = {"valid_images": len(rows), "invalid_images": invalid,
             "exact_duplicate_groups": [paths for paths in hashes.values() if len(paths) > 1],
             "classes": dict(sorted(Counter(row["label"] for row in rows).items()))}
    return rows, audit


def split_rows(rows, seed=42):
    grouped = defaultdict(lambda: defaultdict(list))
    for row in rows:
        grouped[row["label"]][row["capture_group"]].append(row)
    result = {"train": [], "validation": [], "test": []}
    randomizer = random.Random(seed)
    for groups in grouped.values():
        group_ids = list(groups); randomizer.shuffle(group_ids)
        total = len(group_ids)
        train_end = max(1, round(total * .70))
        validation_end = max(train_end + 1, round(total * .85))
        validation_end = min(validation_end, total - 1) if total >= 3 else total
        for name, selected in (("train", group_ids[:train_end]), ("validation", group_ids[train_end:validation_end]), ("test", group_ids[validation_end:])):
            for group_id in selected: result[name].extend(groups[group_id])
    return result


def write_manifest(path, rows, readonly=False):
    if path.exists() and not os.access(path, os.W_OK):
        path.chmod(stat.S_IWRITE | stat.S_IREAD)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader(); writer.writerows(sorted(rows, key=lambda row: (row["label"], row["path"])))
    if readonly: path.chmod(stat.S_IREAD)


def main(raw_path, output_path):
    raw_dir, output_dir = Path(raw_path), Path(output_path)
    if not raw_dir.is_dir(): raise SystemExit(f"Raw dataset folder not found: {raw_dir}")
    rows, audit = audit_raw_dataset(raw_dir)
    if not rows: raise SystemExit("No valid images found")
    splits = split_rows(rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_manifest(output_dir / "all.csv", rows)
    write_manifest(output_dir / "train.csv", splits["train"])
    write_manifest(output_dir / "validation.csv", splits["validation"])
    write_manifest(output_dir / "test.csv", splits["test"], readonly=True)
    audit["split_counts"] = {name: len(values) for name, values in splits.items()}
    (output_dir / "audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit["split_counts"], indent=2))


if __name__ == "__main__": main(*sys.argv[1:])
