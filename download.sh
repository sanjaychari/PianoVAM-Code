#!/bin/bash
# PianoVAM dataset download launcher
# Run from project root: ./download.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate conda env if available
if command -v conda &> /dev/null; then
    eval "$(conda shell.bash hook)"
    conda activate pianoVAM 2>/dev/null || true
fi

# Interactive mode when no args
if [[ $# -eq 0 ]] && [[ -t 0 ]]; then
    echo ""
    echo "=== PianoVAM Dataset Download ==="
    echo ""
    echo "Modalities: 1=audio, 2=video, 3=midi, 4=handskeleton, 5=tsv"
    read -p "Select modalities (comma-separated numbers, or 'a' for all) [a]: " mod_sel
    mod_sel="${mod_sel:-a}"

    echo ""
    echo "Splits: 1=train, 2=validation, 3=test"
    read -p "Select splits (comma-separated numbers, or 'a' for all) [a]: " split_sel
    split_sel="${split_sel:-a}"

    echo ""
    echo "Output directory: where to save downloaded files (relative to project root or absolute path)"
    read -p "Output directory [PianoVAM_v1.0]: " out_dir
    out_dir="${out_dir:-PianoVAM_v1.0}"

    # Convert modality selection to names
    if [[ "$mod_sel" == "a" ]]; then
        mod_arg=""
    else
        mod_map="1:audio 2:video 3:midi 4:handskeleton 5:tsv"
        mod_list=""
        for n in $(echo "$mod_sel" | tr ',' ' '); do
            n=$(echo "$n" | tr -d ' ')
            case "$n" in
                1) mod_list="${mod_list}audio," ;;
                2) mod_list="${mod_list}video," ;;
                3) mod_list="${mod_list}midi," ;;
                4) mod_list="${mod_list}handskeleton," ;;
                5) mod_list="${mod_list}tsv," ;;
            esac
        done
        mod_arg="-m ${mod_list%,}"
    fi

    # Convert split selection to names
    if [[ "$split_sel" == "a" ]]; then
        split_arg=""
    else
        split_list=""
        for n in $(echo "$split_sel" | tr ',' ' '); do
            n=$(echo "$n" | tr -d ' ')
            case "$n" in
                1) split_list="${split_list}train," ;;
                2) split_list="${split_list}validation," ;;
                3) split_list="${split_list}test," ;;
            esac
        done
        split_arg="-s ${split_list%,}"
    fi

    echo ""
    echo "Starting download..."
    exec python PreProcessing/Dataset-Download/download_pianovam.py $mod_arg $split_arg -o "$out_dir"
else
    python PreProcessing/Dataset-Download/download_pianovam.py "$@"
fi
