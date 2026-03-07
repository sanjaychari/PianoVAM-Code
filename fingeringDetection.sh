#!/bin/bash
# ASDF (semi-Automated System for Detecting Fingering) launcher
# Run from project root: ./fingeringDetection.sh

cd "$(dirname "$0")"
streamlit run ./FingeringDetection/ASDF.py "$@"
