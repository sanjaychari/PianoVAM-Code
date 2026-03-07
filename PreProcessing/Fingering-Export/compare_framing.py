"""
Compare fingering accuracy: onset*60 vs miditotoken frame alignment.

Exports GT files with both methods, evaluates, and prints comparison.
Run: python PreProcessing/Fingering-Export/compare_framing.py
"""
import os
import subprocess
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
DATASET = _PROJECT_ROOT / "PianoVAM_v1.0"
OUT_DEFAULT = DATASET / "Fingering"
OUT_MIDITOKEN = DATASET / "Fingering-miditotoken"

# GT basenames for comparison
GT_BASENAMES = [
    "2024-02-15_20-07-54", "2024-02-15_21-40-43", "2024-02-15_21-57-38",
    "2024-02-17_21-44-37", "2024-02-17_22-33-45", "2024-02-22_11-58-09",
    "2024-03-11_22-23-29", "2024-04-08_22-49-18",
]


def run_export_gt(use_miditotoken):
    """Export only GT files."""
    out_dir = OUT_MIDITOKEN if use_miditotoken else OUT_DEFAULT
    files_arg = ",".join(GT_BASENAMES)
    cmd = [
        sys.executable, str(_SCRIPT_DIR / "export_fingering.py"),
        "--format", "json", "--output-dir", str(out_dir),
        "--files", files_arg,
    ]
    if use_miditotoken:
        cmd.append("--use-miditotoken")
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(_PROJECT_ROOT), timeout=600)


def run_evaluate(input_dir):
    return subprocess.run(
        [sys.executable, str(_SCRIPT_DIR / "evaluate_fingering.py"), "--input-dir", str(input_dir)],
        capture_output=True, text=True, cwd=str(_PROJECT_ROOT), timeout=60,
    )


def main():
    print("=" * 60)
    print("Frame alignment comparison: onset*60 vs miditotoken")
    print("=" * 60)

    # Evaluate default (onset*60) - already exported
    print("\n1. Evaluating default (onset*60) export...")
    r1 = run_evaluate(OUT_DEFAULT)
    if r1.returncode != 0:
        print("   [WARN] Default eval failed:", r1.stderr[:200])
    else:
        print(r1.stdout)

    # Export with miditotoken
    print("\n2. Exporting with miditotoken (GT files only)...")
    r2 = run_export_gt(use_miditotoken=True)
    if r2.returncode != 0:
        print("   [ERROR] miditotoken export failed:", r2.stderr[:300])
        return
    print("   Done.")

    # Evaluate miditotoken
    print("\n3. Evaluating miditotoken export...")
    r3 = run_evaluate(OUT_MIDITOKEN)
    if r3.returncode != 0:
        print("   [WARN] miditotoken eval failed:", r3.stderr[:200])
    else:
        print(r3.stdout)

    print("\n" + "=" * 60)
    print("Comparison complete. Check Micro/Macro exact match above.")
    print("=" * 60)


if __name__ == "__main__":
    main()
