# Fingering Export

Export per-note fingering from `PianoVAM_v1.0/fingering_pickles` and `MIDI/` to TSV/JSON.

## Prerequisites

- `PianoVAM_v1.0/fingering_pickles/` with `fingering_*.pkl` (keyhandlist) or `fingerinfo_*.pkl`
- `PianoVAM_v1.0/MIDI/` with `.mid` files
- Optional: `PianoVAM_v1.0/TSV/` for key_offset/frame_offset reference

**Note**: `fingering_*.pkl` (keyhandlist) is converted to per-note fingerinfo via `decider_standalone.decide_fingering`. Full export may take 1–2 hours for ~105 files (O(notes×frames) per file).

## Usage

### 1. Inspect data structure

```bash
python PreProcessing/Fingering-Export/inspect_data.py
```

### 2. Export fingering

```bash
# Export both TSV and JSON (default)
python PreProcessing/Fingering-Export/export_fingering.py

# TSV only
python PreProcessing/Fingering-Export/export_fingering.py --format tsv

# Use existing TSV for key_offset/frame_offset
python PreProcessing/Fingering-Export/export_fingering.py --use-tsv-ref

# Limit to first 5 files
python PreProcessing/Fingering-Export/export_fingering.py --limit 5
```

### 3. Evaluate against ground truth

```bash
python PreProcessing/Fingering-Export/evaluate_fingering.py

# Custom input directory
python PreProcessing/Fingering-Export/evaluate_fingering.py --input-dir path/to/Fingering
```

Reports exact match (hand+finger) and hand-only accuracy for 11 GT recordings.

## Output

- **TSV**: `onset`, `key_offset`, `frame_offset`, `note`, `velocity`, `finger`
- **JSON**: `{ "notes": [{ "onset", "offset", "pitch", "velocity", "finger" }] }`
- Default output: `PianoVAM_v1.0/Fingering/`
