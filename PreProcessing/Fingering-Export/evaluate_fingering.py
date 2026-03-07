"""
Evaluate exported fingering against ground truth (fingergt.py).

Usage:
  python PreProcessing/Fingering-Export/evaluate_fingering.py
  python PreProcessing/Fingering-Export/evaluate_fingering.py --input-dir path/to/Fingering
"""
import argparse
import json
import os
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
# Project root: PreProcessing/Fingering-Export -> parent.parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
sys.path.insert(0, str(_SCRIPT_DIR))
import config

# Load GT without FingeringDetection package (avoids import path issues)
import importlib.util
_fingergt_path = _PROJECT_ROOT / "FingeringDetection" / "detection" / "fingergt.py"
_spec = importlib.util.spec_from_file_location("fingergt", str(_fingergt_path))
_fingergt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fingergt)
GT_MAP = _fingergt.GT_MAP


def from_internal(v):
    """Convert legacy 1-10 to (hand, finger)."""
    if v <= 5:
        return ("L", v)
    return ("R", v - 5)


def parse_prediction(note):
    """
    Parse prediction from JSON note. Supports:
    - hand + finger (separate)
    - finger as int 1-10
    - finger as "L1", "R5" (combined)
    Returns (hand, finger) or (None, None) for Noinfo/unknown.
    """
    hand = note.get("hand")
    finger = note.get("finger")

    if hand is not None and finger is not None and finger != "Noinfo":
        if isinstance(finger, int) and 1 <= finger <= 5 and hand in ("L", "R"):
            return (hand, finger)

    if finger is None or finger == "Noinfo":
        return (None, None)

    if isinstance(finger, int) and 1 <= finger <= 10:
        return from_internal(finger)

    if isinstance(finger, str) and len(finger) >= 2:
        h = finger[0]
        try:
            f = int(finger[1])
            if h in ("L", "R") and 1 <= f <= 5:
                return (h, f)
        except ValueError:
            pass

    return (None, None)


def evaluate_one(basename, pred_path, gt_list):
    """Evaluate one file. Returns (exact, hand_ok, total, noinfo_count)."""
    if not os.path.exists(pred_path):
        return None

    with open(pred_path) as f:
        data = json.load(f)
    notes = data.get("notes", [])
    n_gt = len(gt_list)

    if len(notes) < n_gt:
        return None

    exact = 0
    hand_ok = 0
    noinfo_count = 0

    for i in range(n_gt):
        gt_hand, gt_finger = gt_list[i]
        pred_hand, pred_finger = parse_prediction(notes[i])

        if pred_hand is None:
            noinfo_count += 1
            continue

        if pred_hand == gt_hand and pred_finger == gt_finger:
            exact += 1
        if pred_hand == gt_hand:
            hand_ok += 1

    total = n_gt
    return (exact, hand_ok, total, noinfo_count)


def main():
    parser = argparse.ArgumentParser(description="Evaluate fingering against GT")
    parser.add_argument("--input-dir", default=None,
                       help="Fingering JSON directory (default: PianoVAM_v1.0/Fingering)")
    args = parser.parse_args()

    if args.input_dir:
        input_dir = args.input_dir
    else:
        input_dir = config.OUTPUT_DIR

    if not os.path.exists(input_dir):
        print(f"Error: Input directory not found: {input_dir}")
        sys.exit(1)

    total_exact = 0
    total_hand = 0
    total_notes = 0
    total_noinfo = 0
    results = []

    for basename, gt_list in sorted(GT_MAP.items()):
        pred_path = os.path.join(input_dir, basename + ".json")
        r = evaluate_one(basename, pred_path, gt_list)
        if r is None:
            print(f"  [SKIP] {basename}: file not found or too few notes")
            continue

        exact, hand_ok, n, noinfo = r
        total_exact += exact
        total_hand += hand_ok
        total_notes += n
        total_noinfo += noinfo

        eval_notes = n - noinfo
        exact_acc = 100 * exact / eval_notes if eval_notes > 0 else 0
        hand_acc = 100 * hand_ok / eval_notes if eval_notes > 0 else 0

        results.append((basename, exact, hand_ok, n, noinfo, exact_acc, hand_acc))
        print(f"  {basename}: exact={exact_acc:.1f}% hand={hand_acc:.1f}% "
              f"(n={n}, noinfo={noinfo})")

    # Per-recording quality table
    print()
    print("=" * 90)
    print("Per-recording quality (sorted by Exact)")
    print("=" * 90)
    print(f"{'Recording':<28} {'Exact%':>10} {'Hand%':>10} {'Eval N':>8} {'Noinfo':>8}")
    print(f"{'':28} {'(hand+finger)':>10} {'(hand only)':>10} {'':8} {'':8}")
    print("-" * 90)
    for r in sorted(results, key=lambda x: -x[5]):
        print(f"{r[0]:<28} {r[5]:>7.1f}% {r[6]:>7.1f}% {r[3]:>5} {r[4]:>7}")
    print("-" * 90)

    if total_notes == 0:
        print("No GT files with predictions found.")
        sys.exit(1)

    eval_notes = total_notes - total_noinfo
    macro_exact = sum(r[5] for r in results) / len(results) if results else 0
    macro_hand = sum(r[6] for r in results) / len(results) if results else 0
    micro_exact = 100 * total_exact / eval_notes if eval_notes > 0 else 0
    micro_hand = 100 * total_hand / eval_notes if eval_notes > 0 else 0

    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"  Files evaluated: {len(results)}")
    print(f"  Total notes (GT): {total_notes}")
    print(f"  Noinfo (excluded): {total_noinfo}")
    print(f"  Evaluable notes: {eval_notes}")
    print()
    print(f"  Micro exact match: {micro_exact:.2f}%")
    print(f"  Micro hand match:  {micro_hand:.2f}%")
    print(f"  Macro exact match: {macro_exact:.2f}%")
    print(f"  Macro hand match:  {macro_hand:.2f}%")


if __name__ == "__main__":
    main()
