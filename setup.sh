#!/bin/bash
# PianoVAM environment setup script
# Creates conda environment 'pianoVAM' and installs all dependencies

set -e

ENV_NAME="pianoVAM"
PYTHON_VERSION="3.10"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "  PianoVAM Environment Setup (conda: $ENV_NAME)"
echo "=========================================="

# 1. Check if conda is available
if ! command -v conda &> /dev/null; then
    echo "Error: conda is not installed. Please install Anaconda or Miniconda first."
    exit 1
fi

# 2. Prompt to remove existing env (skip in non-interactive mode)
if [[ -t 0 ]] && conda env list | grep -q "^${ENV_NAME} "; then
    echo ""
    read -p "Environment '$ENV_NAME' already exists. Remove and recreate? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        conda env remove -n "$ENV_NAME" -y
    else
        echo "Keeping existing environment and updating packages."
    fi
fi

# 3. Create conda environment (if not exists)
if ! conda env list | grep -q "^${ENV_NAME} "; then
    echo ""
    echo "[1/3] Creating conda environment (Python $PYTHON_VERSION)..."
    conda create -n "$ENV_NAME" python="$PYTHON_VERSION" -y
fi

# 4. Activate environment and install packages
echo ""
echo "[2/3] Installing pip packages..."
eval "$(conda shell.bash hook)"
conda activate "$ENV_NAME"

# Check if requirements.txt exists
if [[ ! -f "requirements.txt" ]]; then
    echo "Error: requirements.txt not found."
    exit 1
fi

pip install --upgrade pip
pip install -r requirements.txt

# 5. System dependency notice (fluidsynth for Audio-MIDI-Alignment)
echo ""
echo "[3/3] Checking system dependencies..."
if ! command -v fluidsynth &> /dev/null; then
    echo ""
    echo "  Warning: fluidsynth is not installed."
    echo "  fluidsynth is required for PreProcessing/Audio-MIDI-Alignment."
    echo ""
    if [[ -f /etc/debian_version ]] || command -v apt-get &> /dev/null; then
        echo "  Ubuntu/Debian: sudo apt-get install fluidsynth fluid-soundfont-gm"
        if [[ -t 0 ]]; then
            echo ""
            read -p "  Install now? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                sudo apt-get update && sudo apt-get install -y fluidsynth fluid-soundfont-gm
            fi
        fi
    else
        echo "  Other Linux: install fluidsynth via your package manager"
        echo "  macOS: brew install fluidsynth"
    fi
else
    echo "  fluidsynth is installed"
fi

echo ""
echo "=========================================="
echo "  Setup complete!"
echo "=========================================="
echo ""
echo "Activate environment: conda activate $ENV_NAME"
echo ""
echo "Usage examples:"
echo "  - ASDF (fingering annotation): streamlit run ./FingeringDetection/ASDF.py"
echo "  - Download dataset: ./download.sh"
echo "  - Audio-MIDI alignment: python PreProcessing/Audio-MIDI-Alignment/main.py"
echo ""
