"""Choose confidence/margin thresholds with max 3% unknown false acceptance.

Input CSV columns: confidence,margin,is_known. Selects the threshold pair with
the most known-image acceptance while respecting the stated safety constraint.
"""
import csv
import json
import sys
from pathlib import Path


def main(input_csv: str, output_json: str):
    rows = [{key: float(value) for key, value in row.items()} for row in csv.DictReader(open(input_csv, encoding="utf-8"))]
    known = [row for row in rows if row["is_known"] == 1]
    unknown = [row for row in rows if row["is_known"] == 0]
    best = None
    for confidence in range(50, 100):
        for margin in range(0, 51):
            unknown_rate = sum(r["confidence"] >= confidence and r["margin"] >= margin for r in unknown) / max(len(unknown), 1)
            known_rate = sum(r["confidence"] >= confidence and r["margin"] >= margin for r in known) / max(len(known), 1)
            if unknown_rate <= .03 and (best is None or known_rate > best[0]): best = (known_rate, confidence, margin, unknown_rate)
    if best is None: raise SystemExit("No threshold meets the 3% false-acceptance target")
    Path(output_json).write_text(json.dumps({"catalog_version": "2026.1", "min_confidence": best[1], "min_margin": best[2], "unknown_false_acceptance": best[3]}, indent=2), encoding="utf-8")


if __name__ == "__main__": main(*sys.argv[1:])
