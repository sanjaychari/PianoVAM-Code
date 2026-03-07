"""
Standalone miditotoken: build tokenlist from MIDI using miditok (beat-based frame alignment).

Returns tokenlist compatible with decide_fingering: [start_frame, pitch_index, end_frame, token_number]
Requires: miditok, symusic
"""
import math
import os


def miditotoken_from_path(midi_path, fps=60):
    """
    Build tokenlist from MIDI file path. Uses miditok for beat-based timing (matches keyhandlist).
    Returns list of [start_frame, pitch_index, end_frame, token_number] or None if deps missing.
    """
    try:
        from symusic import Score
        from miditok import REMI, TokenizerConfig
    except ImportError:
        return None

    if not os.path.exists(midi_path):
        return None

    midi = Score(midi_path)
    if not midi.tempos:
        tempo = 120
    else:
        tempo = midi.tempos[0].qpm
    beatres = math.floor(fps * 60 / tempo)

    config = TokenizerConfig(
        num_velocities=16,
        use_chords=False,
        use_programs=True,
        beat_res={(0, 100): beatres},
    )
    tokenizer = REMI(config)
    tokens = tokenizer(midi)

    # Split by Duration tokens (each note ends with Duration)
    tokenlist = []
    tempindex = 0
    for i in range(len(tokens.tokens)):
        if "Duration" in str(tokens.tokens[i]):
            tokenlist.append(tokens.tokens[tempindex : i + 1])
            tempindex = i + 1

    # Simplify: [Position, Pitch, Duration] -> [start_pos, pitch-21, end_pos, idx]
    for token in tokenlist:
        while "Bar" in str(token[0]):
            token.pop(0)
            token.append("Bar")
    positionindex = 0
    for i in range(len(tokenlist)):
        token = tokenlist[i]
        if "Position" not in str(token[0]):
            token.insert(0, tokenlist[positionindex][0])
        else:
            positionindex = i
    barcounter = -1
    for token in tokenlist:
        while "Bar" in str(token[-1]):
            token.pop(-1)
            barcounter += 1
        token[0] = int(str(token[0])[9:]) + 4 * beatres * barcounter

    for token in tokenlist:
        token.pop(1)
        token[1] = int(str(token[1])[6:]) - 21  # Pitch_70 -> 70-21
        token.pop(2)
        d = str(token[2])  # Duration_0.17.30
        parts = d.split(".")
        token[2] = token[0] + int(parts[0][9:]) * beatres + int(parts[1])  # end = start + duration
    for i in range(len(tokenlist)):
        tokenlist[i].append(i)

    return tokenlist
