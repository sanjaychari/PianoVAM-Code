# Fingering Quality Analysis

## Current Results (7 GT files)

| Metric | Value |
|--------|-------|
| Micro exact match | 57.92% |
| Micro hand match | 77.75% |
| Hand errors | 22.2% |
| Finger errors (hand correct) | 19.8% |

## Error Breakdown by Recording

| Recording | Exact | Hand wrong | Finger wrong |
|-----------|-------|------------|--------------|
| 2024-02-22_11-58-09 | 95.3% | 0% | 4.7% |
| 2024-02-17_21-44-37 | 78.5% | 5.8% | 15.7% |
| 2024-02-15_20-07-54 | 74.0% | 10.6% | 15.4% |
| 2024-02-15_21-40-43 | 56.2% | 24.1% | 19.6% |
| 2024-03-11_22-23-29 | 52.9% | 25.5% | 21.6% |
| 2024-02-15_21-57-38 | 34.4% | 37.5% | 28.1% |
| 2024-02-17_22-33-45 | 35.0% | 37.9% | 27.1% |

Quality varies greatly by recording (35%–95% exact). Best case has 0% hand errors.

## Potential Causes

### 1. Frame alignment mismatch (data extraction)

**Our pipeline:**
- `start_frame = int(onset * 60)`, `end_frame = int(offset * 60)`
- Uses `pretty_midi` for onset/offset (seconds)

**ASDF pipeline (keyhandlist source):**
- `miditotoken(MIDI, fps, "simplified")` → beat-based positions
- `beatres = fps * 60 / tempo` → positions align with frames when tempo is constant
- Uses `miditok` + `symusic` for tokenization

**Risk:** If PianoVAM MIDI has tempo changes or different timing than ASDF's `_singletempo` MIDI, frame indices can drift. Notes may map to wrong keyhandlist frames.

### 2. MIDI file difference

- **ASDF:** Uses `midiconvert/*_singletempo.mid` (tempo-unified)
- **Our export:** Uses `PianoVAM_v1.0/MIDI/*.mid` (raw)

Different MIDI files → different note order or onset times → token index mismatch.

### 3. Keyhandlist generation (upstream)

`fingering_*.pkl` comes from ASDF `handfingercorresponder`:
- MediaPipe hand detection → hand landmarks
- Keyboard calibration (4 corners) → key regions
- Per-frame: which hand/finger is nearest to each pressed key

**Limitations:**
- Hand detection noise (occlusion, lighting)
- Keyboard calibration errors
- Top-view geometry (finger overlap, perspective)

### 4. Decider thresholds

`decider_standalone.decide_fingering`:
- Finger score &lt; 0.5 of totalframe → discard
- Finger score &gt; 0.8 → high-confidence
- Multiple high candidates → undecided (exported as Noinfo or first candidate)

Thresholds may be too strict or too loose for some pieces.

## Recommended Actions

1. **Verify MIDI alignment:** Compare note order and onset times between `PianoVAM_v1.0/MIDI/*.mid` and ASDF's `_singletempo` MIDI. Ensure we use the same MIDI that generated the keyhandlist.

2. **Use miditotoken for tokenlist:** If ASDF's miditok path is available, use `miditotoken` instead of `onset*60` for frame alignment. This would require `miditok` and `symusic` dependencies.

3. **Diagnose per-recording:** Run `diagnose_quality.py` to see hand vs finger error patterns. Recordings with high hand error may have calibration or visibility issues.

4. **Tune decider:** Experiment with 0.5/0.8 thresholds or add onset-weighted scoring (frames near note onset matter more).

5. **Consider undecidedfingerlist:** ASDF's manual label tab can correct undecided notes. If `undecidedfingerlist_*.pkl` exists with manual labels, merge them into the export.
