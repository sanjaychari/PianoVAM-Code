# Strategy: Per-Note Fingering Export from PianoVAM Dataset

## Goal
Use `PianoVAM_v1.0/fingering_pickles` (or `Handskeleton/`) and `PianoVAM_v1.0/MIDI/` to produce per-note fingering annotations.

---

## Data Inventory

### 1. PianoVAM Dataset Structure
```
PianoVAM_v1.0/
├── MIDI/           # .mid files (e.g., 2024-02-14_19-10-09.mid)
├── Handskeleton/   # .json files – MediaPipe 21 keypoints per hand, per frame
├── TSV/            # velocity, note, frame_offset, key_offset, onset (no fingering)
├── Audio/, Video/
└── metadata_v2.json
```

### 2. ASDF Pipeline Outputs (when run on video)
```
videocapture/<video>_<conf>/
├── handlist_*.pkl          # Per-frame hand landmarks (MediaPipe)
├── floatingframes_*.pkl    # Hand depth/floating state
├── fingerinfo_*.pkl        # Per-note finger (1–10 or "Noinfo")  ← target
└── undecidedfingerlist_*.pkl
```

### 3. Key Mappings
- **Finger encoding**: 1–5 = Left (thumb→pinky), 6–10 = Right (thumb→pinky)
- **Note index**: Matches MIDI note order (note_on events)
- **File matching**: `2024-02-14_19-10-09` → MIDI, Handskeleton, TSV share same base name

---

## Strategy Options

### Option A: Use Pre-computed `fingerinfo_*.pkl` (if available)

**When**: ASDF has already been run and `fingerinfo_*.pkl` exists in `fingering_pickles/` or similar.

**Steps**:
1. For each MIDI file in `PianoVAM_v1.0/MIDI/`:
   - Get base name (e.g., `2024-02-14_19-10-09`)
   - Find matching `fingerinfo_<basename>_<conf>.pkl`
2. Parse MIDI to get note list (onset, pitch, velocity, note index)
3. Align `fingerinfo[i]` with note index `i`
4. Export to chosen format (TSV, JSON, MIDI text events)

**Output format example (TSV)**:
```
note_index  onset  offset  pitch  velocity  finger
0           0.12   0.45    60     80        3
1           0.50   0.72    64     90        5
```

---

### Option B: Use `Handskeleton/` JSON (dataset-native)

**When**: Only `Handskeleton/` JSON is available (no ASDF pickles).

**Challenges**:
- Handskeleton JSON format may differ from ASDF `handlist`
- ASDF needs **keyboard coordinates** (4 corners) for key–hand mapping
- Dataset metadata has `Point_LT`, `Point_RT`, `Point_RB`, `Point_LB` per recording

**Steps**:
1. **Handskeleton → handlist conversion**
   - Parse JSON to match ASDF `handclass(handtype, handlandmark, handframe)`
   - Normalize coordinates if needed (e.g., [0,1] vs [-1,1])
2. **Keyboard setup**
   - Use `Point_LT/RB` from metadata as keyboard corners
   - Or use default 88-key layout if metadata format is known
3. **Reuse ASDF pipeline**
   - `handpositiondetector` → `handfingercorresponder` → `decide_fingering`
   - Requires: `floatingframes` (can be derived or approximated)
4. **MIDI alignment**
   - Use `miditotoken` + `tokentoframeinfo` with video FPS (e.g., 60)
   - FPS can come from metadata or be fixed (e.g., 60 for PianoVAM)

---

### Option C: Hybrid – Handskeleton + TSV (simplified)

**When**: Full ASDF pipeline is too heavy or keyboard calibration is missing.

**Idea**: Use TSV for note timing and Handskeleton for hand presence only.

**Steps**:
1. TSV gives: `onset`, `key_offset`, `note`, `velocity` per note
2. Map onset → frame index: `frame = round(onset * fps)`
3. From Handskeleton at that frame, infer left/right hand only (no finger)
4. Export: `(note, onset, offset, pitch, velocity, hand)` with hand = L/R/Unknown

**Limitation**: No finger number (1–10), only hand.

---

## Recommended Path

### Phase 1: Verify Data
1. List contents of `PianoVAM_v1.0/fingering_pickles` and `PianoVAM_v1.0/Handskeleton`
2. Check for `fingerinfo_*.pkl` or `handlist_*.pkl`
3. Inspect one Handskeleton JSON to confirm structure

### Phase 2: Implement Based on What Exists

| Data available              | Approach                          |
|----------------------------|-----------------------------------|
| `fingerinfo_*.pkl`         | Option A – direct export          |
| `handlist_*.pkl` + keyboard| Run `handfingercorresponder` → `decide_fingering` → export |
| `Handskeleton/` only       | Option B or C                     |

### Phase 3: Export Format
- **TSV**: Add `finger` column to existing TSV schema
- **JSON**: `{ "notes": [{ "onset", "offset", "pitch", "velocity", "finger" }, ...] }`
- **MIDI text**: Use MIDI text meta events or a sidecar file

---

## Implementation Outline

```
PreProcessing/Fingering-Export/
├── export_fingering.py    # Main script
├── align_midi_fingering.py # MIDI ↔ fingerinfo alignment
└── README.md
```

**Core logic**:
1. `load_fingerinfo(pkl_path)` → list of finger per note index
2. `load_midi_notes(midi_path)` → list of (onset, offset, pitch, velocity, index)
3. `align_and_export(fingerinfo, notes, output_path, format="tsv")`
4. Batch over all MIDI files with matching fingerinfo

---

## Dependencies
- Existing: `mido`, `pretty_midi`, `miditok`, `symusic` (for tokenlist)
- Fingering logic: `FingeringDetection/detection/decider`, `midicomparison`
