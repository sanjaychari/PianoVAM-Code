"""
FingeringDetection configuration and path constants
"""
import os

# Base paths (relative to ASDF.py)
_FINGERING_DIR = os.path.dirname(os.path.abspath(__file__))

# Data directories
MIDI_DIR = os.path.join(_FINGERING_DIR, "midiconvert")
VIDEO_DIR = os.path.join(_FINGERING_DIR, "videocapture")

# MediaPipe model path
HAND_LANDMARKER_PATH = os.path.join(_FINGERING_DIR, "hand_landmarker.task")

# Keyboard coordinate info
KEYBOARD_COORDINATE_PATH = os.path.join(_FINGERING_DIR, "keyboardcoordinateinfo.pkl")
KEYBOARD_CORNER_PATHS = {
    "lu": os.path.join(_FINGERING_DIR, "lu.pkl"),
    "ld": os.path.join(_FINGERING_DIR, "ld.pkl"),
    "ru": os.path.join(_FINGERING_DIR, "ru.pkl"),
    "rd": os.path.join(_FINGERING_DIR, "rd.pkl"),
}

# Output files (CWD-based, legacy compatibility)
FINGERING_TXT = "fingering.txt"
COMPLETE_FINGERING_TXT = "completefingering.txt"

# Video path (used by main.py, user-configurable)
def get_video_path():
    """videocapture path. Synced with main.py filepath."""
    return os.path.join(os.path.expanduser("~"), "ASDF", "PianoVAM", "FingeringDetection", "videocapture")
