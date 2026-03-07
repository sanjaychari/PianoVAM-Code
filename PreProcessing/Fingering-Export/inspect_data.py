"""
Phase 1: Inspect fingering_pickles and MIDI structure.
Run from project root: python PreProcessing/Fingering-Export/inspect_data.py
"""
import os
import sys
import pickle
import glob
from pathlib import Path

import pretty_midi

# Add script directory for config import
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCRIPT_DIR)
import config as _config
FINGERING_PICKLES_DIR = _config.FINGERING_PICKLES_DIR
MIDI_DIR = _config.MIDI_DIR


def inspect_fingering_pickles():
    """Inspect fingering_pickles directory structure and sample pkl contents."""
    print("=" * 60)
    print("1. FINGERING_PICKLES INSPECTION")
    print("=" * 60)

    if not os.path.exists(FINGERING_PICKLES_DIR):
        print(f"[WARN] Directory not found: {FINGERING_PICKLES_DIR}")
        print("       Create it or run ASDF to generate fingerinfo pkl files.")
        return False

    files = sorted(os.listdir(FINGERING_PICKLES_DIR))
    print(f"Directory: {FINGERING_PICKLES_DIR}")
    print(f"Total files: {len(files)}")

    fingerinfo_files = [f for f in files if f.startswith("fingerinfo_") and f.endswith(".pkl")]
    fingering_files = [f for f in files if f.startswith("fingering_") and f.endswith(".pkl")]
    handlist_files = [f for f in files if f.startswith("handlist_") and f.endswith(".pkl")]
    undecided_files = [f for f in files if f.startswith("undecidedfingerlist_") and f.endswith(".pkl")]

    print(f"  fingerinfo_*.pkl: {len(fingerinfo_files)}")
    print(f"  fingering_*.pkl: {len(fingering_files)} (keyhandlist format)")
    print(f"  handlist_*.pkl: {len(handlist_files)}")
    print(f"  undecidedfingerlist_*.pkl: {len(undecided_files)}")

    sample_files = fingerinfo_files or fingering_files
    if not sample_files:
        print("[WARN] No fingerinfo_*.pkl or fingering_*.pkl files found.")
        return False

    # Load first sample
    sample_path = os.path.join(FINGERING_PICKLES_DIR, sample_files[0])
    print(f"\nSample: {sample_files[0]}")
    with open(sample_path, "rb") as f:
        data = pickle.load(f)

    print(f"  type: {type(data)}")
    print(f"  len: {len(data)}")
    if len(data) > 0:
        print(f"  data[0]: {data[0]} (type: {type(data[0])})")
        if len(data) > 400:
            non_empty = next((i for i, x in enumerate(data) if len(x) > 0), None)
            if non_empty is not None:
                print(f"  data[{non_empty}] (first non-empty): {data[non_empty][:1]}")
        if fingerinfo_files:
            noinfo_count = sum(1 for x in data if x == "Noinfo")
            print(f"  Noinfo count: {noinfo_count} ({100*noinfo_count/len(data):.1f}%)")

    return True


def inspect_midi():
    """Inspect MIDI directory and note order."""
    print("\n" + "=" * 60)
    print("2. MIDI INSPECTION")
    print("=" * 60)

    if not os.path.exists(MIDI_DIR):
        print(f"[WARN] Directory not found: {MIDI_DIR}")
        return False

    midi_files = sorted(glob.glob(os.path.join(MIDI_DIR, "*.mid")))
    print(f"Directory: {MIDI_DIR}")
    print(f"Total .mid files: {len(midi_files)}")

    if not midi_files:
        print("[WARN] No MIDI files found.")
        return False

    # Parse first MIDI
    sample_path = midi_files[0]
    basename = Path(sample_path).stem
    print(f"\nSample: {Path(sample_path).name}")

    midi = pretty_midi.PrettyMIDI(sample_path)
    notes = [note for inst in midi.instruments for note in inst.notes]
    notes.sort(key=lambda n: n.start)

    print(f"  Note count: {len(notes)}")
    if len(notes) > 0:
        n = notes[0]
        print(f"  First note: onset={n.start:.3f}, end={n.end:.3f}, pitch={n.pitch}, vel={n.velocity}")
        if len(notes) > 1:
            n = notes[1]
            print(f"  Second note: onset={n.start:.3f}, end={n.end:.3f}, pitch={n.pitch}, vel={n.velocity}")

    return True


def verify_matching():
    """Verify MIDI-fingerinfo file matching and length alignment."""
    print("\n" + "=" * 60)
    print("3. FILE MATCHING VERIFICATION")
    print("=" * 60)

    if not os.path.exists(FINGERING_PICKLES_DIR) or not os.path.exists(MIDI_DIR):
        print("[SKIP] Required directories not found.")
        return

    midi_files = {Path(p).stem: p for p in glob.glob(os.path.join(MIDI_DIR, "*.mid"))}
    fingerinfo_files = glob.glob(os.path.join(FINGERING_PICKLES_DIR, "fingerinfo_*.pkl"))
    fingering_files = glob.glob(os.path.join(FINGERING_PICKLES_DIR, "fingering_*.pkl"))
    use_fingering = not fingerinfo_files and fingering_files
    fingerinfo_files = fingerinfo_files or fingering_files

    # Build basename -> pkl path
    # Format: fingerinfo_2024-02-14_19-10-09.mp4_85805.pkl or fingering_2024-02-14_19-10-09.pkl
    pkl_by_basename = {}
    for p in fingerinfo_files:
        name = Path(p).stem
        if name.startswith("fingerinfo_"):
            rest = name.replace("fingerinfo_", "")
            if ".mp4_" in rest:
                base = rest.split(".mp4_")[0]
            else:
                parts = rest.rsplit("_", 1)
                base = parts[0] if len(parts) == 2 else rest
        elif name.startswith("fingering_"):
            base = name.replace("fingering_", "")
        else:
            continue
        pkl_by_basename[base] = p

    matched = 0
    mismatched_len = []
    # Limit verification when using decide_fingering (slow: O(notes*frames))
    verify_limit = 3 if use_fingering else None
    verified_count = 0
    for base, midi_path in sorted(midi_files.items()):
        if verify_limit is not None and verified_count >= verify_limit:
            break
        pkl_path = pkl_by_basename.get(base)
        if not pkl_path:
            continue
        verified_count += 1

        with open(pkl_path, "rb") as f:
            pkl_data = pickle.load(f)

        midi = pretty_midi.PrettyMIDI(midi_path)
        notes = [n for inst in midi.instruments for n in inst.notes]
        notes.sort(key=lambda n: n.start)

        # fingering_*.pkl = keyhandlist (need decide_fingering); fingerinfo_*.pkl = direct
        if Path(pkl_path).stem.startswith("fingerinfo_"):
            fingerinfo = pkl_data
            fi_len = len(fingerinfo)
        else:
            # keyhandlist: run decide_fingering to get fingerinfo
            try:
                from decider_standalone import decide_fingering
                fps = 60
                tokenlist = []
                for i, n in enumerate(notes):
                    tokenlist.append([
                        int(n.start * fps),
                        max(0, min(87, n.pitch - 21)),
                        int(n.end * fps),
                        i,
                    ])
                tokenlist_copy = [list(t) for t in tokenlist]
                fingerinfo, _ = decide_fingering(tokenlist_copy, pkl_data)
                fi_len = len(fingerinfo)
            except Exception as e:
                print(f"  [SKIP] {base}: decide_fingering error: {e}")
                continue

        if fi_len == len(notes):
            matched += 1
        else:
            mismatched_len.append((base, fi_len, len(notes)))

    print(f"MIDI files: {len(midi_files)}")
    print(f"fingerinfo pkl files: {len(pkl_by_basename)}")
    if verify_limit:
        print(f"(Verified sample of {verified_count} pairs; keyhandlist format is slow)")
    print(f"Matched pairs with same length: {matched}")
    if mismatched_len:
        print(f"Mismatched length: {len(mismatched_len)}")
        for base, flen, mlen in mismatched_len[:5]:
            print(f"  {base}: fingerinfo={flen}, midi_notes={mlen}")


def main():
    print("Fingering Dataset - Data Structure Inspection\n")
    inspect_fingering_pickles()
    inspect_midi()
    verify_matching()
    print("\nDone.")


if __name__ == "__main__":
    main()
