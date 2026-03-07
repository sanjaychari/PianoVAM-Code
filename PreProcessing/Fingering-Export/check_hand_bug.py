"""
Hand prediction bug checks:
1. Whether decider's hand is discarded when finger=Noinfo in export
2. Systematic L/R swap detection
3. keyhandlist[3] index error (0-based vs 1-based)
"""
import json
import pickle
import os
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
sys.path.insert(0, str(_SCRIPT_DIR))
import config

# Load GT
import importlib.util
_fingergt_path = _PROJECT_ROOT / "FingeringDetection" / "detection" / "fingergt.py"
_spec = importlib.util.spec_from_file_location("fingergt", str(_fingergt_path))
_fingergt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fingergt)
GT_MAP = _fingergt.GT_MAP


def check_keyhandlist_structure():
    """Check keyhandlist[3] (fingercount) structure - indices 0~10 vs 1~10"""
    pickles_dir = Path(config.DATASET_ROOT) / "fingering_pickles"
    if not pickles_dir.exists():
        print("  [SKIP] pickles dir not found")
        return
    pkl_files = list(pickles_dir.glob("fingering_*.pkl"))[:1]
    if not pkl_files:
        print("  [SKIP] no fingering pkl found")
        return
    with open(pkl_files[0], "rb") as f:
        data = pickle.load(f)
    # keyhandlist[j] = [[key, tokennumber, hand, fingercount], ...]
    for j, frame in enumerate(data[:3]):
        for kh in frame[:2]:
            if len(kh) >= 4:
                fc = kh[3]
                print(f"  keyhandinfo[3] type={type(fc).__name__}, len={len(fc) if hasattr(fc,'__len__') else 'N/A'}")
                if hasattr(fc, '__len__') and len(fc) >= 10:
                    print(f"    indices 0-9: {[fc[i] for i in range(min(11, len(fc)))]}")
                    try:
                        for k in range(1, 11):
                            _ = fc[k]
                        print(f"    keyhandinfo[3][1..10] access OK")
                    except IndexError as e:
                        print(f"    BUG: keyhandinfo[3][k] IndexError: {e}")
                break
        break


def check_hand_discarded():
    """Check if decider's hand is discarded when finger=Noinfo"""
    from decider_standalone import decide_fingering
    import pretty_midi

    pickles_dir = Path(config.DATASET_ROOT) / "fingering_pickles"
    midi_dir = Path(config.DATASET_ROOT) / "MIDI"
    basename = "2024-02-15_20-07-54"  # 27 noinfo
    pkl_path = pickles_dir / f"fingering_{basename}.pkl"
    midi_path = midi_dir / f"{basename}.mid"
    if not pkl_path.exists() or not midi_path.exists():
        print("  [SKIP] files not found")
        return

    with open(pkl_path, "rb") as f:
        keyhandlist = pickle.load(f)
    midi = pretty_midi.PrettyMIDI(str(midi_path))
    notes = [n for inst in midi.instruments for n in inst.notes]
    notes.sort(key=lambda n: n.start)

    tokenlist = []
    for i, n in enumerate(notes[:200]):  # first 200 only
        tokenlist.append([
            int(n.start * 60),
            max(0, min(87, n.pitch - 21)),
            int(n.end * 60),
            i,
        ])
    tokenlist_copy = [list(t) for t in tokenlist]
    pressedfingerlist, _ = decide_fingering(tokenlist_copy, keyhandlist)

    # tokenlist_copy is mutated - tokenlist[i][-1] = hand (Left/Right/Noinfo)
    noinfo_with_hand = 0
    noinfo_total = 0
    for i in range(min(150, len(pressedfingerlist))):
        if pressedfingerlist[i] == "Noinfo" or pressedfingerlist[i] is None:
            noinfo_total += 1
            hand = tokenlist_copy[i][-1] if len(tokenlist_copy[i]) > 4 else None
            if hand in ("Left", "Right"):
                noinfo_with_hand += 1
                if noinfo_with_hand <= 3:
                    print(f"    note {i}: finger=Noinfo but decider hand={hand} (discarded!)")

    print(f"  Notes with finger=Noinfo where decider has hand: {noinfo_with_hand}/{noinfo_total}")
    if noinfo_with_hand > 0:
        print(f"  --> BUG: {noinfo_with_hand} notes have hand discarded at export")


def check_lr_swap():
    """Check if hand errors are systematic L<->R swap"""
    input_dir = config.OUTPUT_DIR
    hand_swap = 0
    hand_other = 0
    for basename, gt_list in list(GT_MAP.items()):
        pred_path = os.path.join(input_dir, basename + ".json")
        if not os.path.exists(pred_path):
            continue
        with open(pred_path) as f:
            data = json.load(f)
        notes = data.get("notes", [])
        n_gt = min(len(gt_list), len(notes))
        for i in range(n_gt):
            gt_h, _ = gt_list[i]
            pred_h = notes[i].get("hand")
            pred_f = notes[i].get("finger")
            if pred_h in (None, "Noinfo") or pred_f in ("Noinfo", None):
                continue
            if pred_h != gt_h:
                if (gt_h == "L" and pred_h == "R") or (gt_h == "R" and pred_h == "L"):
                    hand_swap += 1
                else:
                    hand_other += 1
    print(f"  Hand errors: L<->R swap {hand_swap}, other {hand_other}")
    if hand_swap > 0 and hand_other == 0:
        print("  --> All hand errors are L<->R swap (systematic swap possible)")


def main():
    print("=" * 60)
    print("Hand prediction bug check")
    print("=" * 60)

    print("\n1. keyhandlist[3] (fingercount) index structure:")
    check_keyhandlist_structure()

    print("\n2. Decider hand discarded when finger=Noinfo:")
    check_hand_discarded()

    print("\n3. Hand error pattern (L/R swap?):")
    check_lr_swap()

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
