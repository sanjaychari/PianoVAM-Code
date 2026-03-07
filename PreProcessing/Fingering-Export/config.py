"""
Configuration for Fingering Export pipeline.
Paths are relative to project root by default.
"""
import os

# Project root (parent of PreProcessing)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Input paths (PianoVAM dataset structure)
DATASET_ROOT = os.path.join(_PROJECT_ROOT, "PianoVAM_v1.0")
FINGERING_PICKLES_DIR = os.path.join(DATASET_ROOT, "fingering_pickles")
MIDI_DIR = os.path.join(DATASET_ROOT, "MIDI")
TSV_DIR = os.path.join(DATASET_ROOT, "TSV")

# Output path
OUTPUT_DIR = os.path.join(DATASET_ROOT, "Fingering")
