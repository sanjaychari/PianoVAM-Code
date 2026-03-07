# FingeringDetection: Automated System for Detecting Fingering (ASDF)
"""
ASDF - semi-Automated System for Detecting Fingering
Streamlit app for video-based piano fingering annotation
"""

# -----------------------------------------------------------------------------
# 1. Configuration and paths
# -----------------------------------------------------------------------------
import os
import sys

_FINGERING_DIR = os.path.dirname(os.path.abspath(__file__))
if _FINGERING_DIR not in sys.path:
    sys.path.insert(0, _FINGERING_DIR)

import math
import pickle

import cv2
import mido
import numpy as np
import pretty_midi
import streamlit as st
from streamlit_image_coordinates import streamlit_image_coordinates
from stqdm import stqdm

import mediapipe as mp

from config import MIDI_DIR, VIDEO_DIR, KEYBOARD_COORDINATE_PATH, KEYBOARD_CORNER_PATHS, FINGERING_TXT, COMPLETE_FINGERING_TXT
from detection.main import (
    filepath,
    min_hand_detection_confidence,
    min_hand_presence_confidence,
    min_tracking_confidence,
    datagenerate,
)
from detection.midicomparison import (
    pitch_list,
    miditotoken,
    tokentoframeinfo,
    handfingercorresponder,
)
from detection.floatinghands import draw_keyboard_on_image, handpositiondetector, generatekeyboard
from detection.decider import decide_fingering
from detection.utils import get_video_fps, delete_smart_tempo, filter_midi_notes
from visualization import stroll

st.set_page_config(layout="wide")

# Paths (from config, relative paths to CWD for legacy compatibility)
mididirectory = MIDI_DIR
videodirectory = VIDEO_DIR


# -----------------------------------------------------------------------------
# 2. Session state and common utilities
# -----------------------------------------------------------------------------
def initialize_state():
    if "index" not in st.session_state:
        st.session_state.index = 0
    if "history" not in st.session_state:
        st.session_state.history = []
    if "responses" not in st.session_state:
        st.session_state.responses = []


def _get_mediapipe_dirname(videoname):
    """MediaPipe processing result directory path"""
    conf_str = f"{min_hand_detection_confidence*100}{min_hand_presence_confidence*100}{min_tracking_confidence*100}"
    return os.path.join(filepath, videoname[:-4] + "_" + conf_str)


def _get_midiname_from_video(selected_option):
    """Parse MIDI/video name from selected option"""
    if "_singletempo.mid" in selected_option:
        newmidiname = selected_option
        videoname = "_".join(selected_option.split("_")[:-1]) + ".mp4"
    else:
        newmidiname = selected_option[:-4] + "_singletempo.mid"
        videoname = selected_option[:-4] + ".mp4"
    return newmidiname, videoname


# -----------------------------------------------------------------------------
# 3. Fingering labeling UI (Label tab)
# -----------------------------------------------------------------------------
def _button_input(undecidedtokeninfolist, fps, videoname, newmidiname):
    """Manual fingering selection UI"""
    if len(undecidedtokeninfolist) == 0:
        st.write("No fingers to choose!")
        return ["Complete"]

    buttons = [tokeninfo[2] for tokeninfo in undecidedtokeninfolist]

    def button_click(button_name):
        if st.session_state.index < len(buttons):
            st.session_state.history.append(st.session_state.index)
            st.session_state.responses.append([button_name[0], undecidedtokeninfolist[st.session_state.index][0]])
            st.session_state.index += 1
        st.rerun()

    def undo():
        if st.session_state.history:
            st.session_state.index = st.session_state.history.pop()
            st.session_state.responses.pop()
        st.rerun()

    def reset():
        st.session_state.index = 0
        st.session_state.history = []
        st.session_state.responses = []
        st.rerun()

    def complete():
        st.session_state.responses.append("Complete")
        return st.session_state.responses

    # Current step UI
    if st.session_state.index < len(buttons):
        tokeninfo = undecidedtokeninfolist[st.session_state.index]
        frame_num = tokeninfo[1][0]
        pitch = tokeninfo[1][1]
        pitch_idx = pitch_list.index(pitch)
        time_sec = frame_num / fps
        ms = math.floor(time_sec % 60 * 1000) / 1000 - math.floor(time_sec % 60)

        st.write(
            f"#### Choose the actual finger which pressed {pitch}({pitch_idx}) at frame {frame_num} "
            f"or time {str(int(time_sec//60)).zfill(2)}:{str(math.floor(time_sec%60)).zfill(2)}:{format(ms, '.2f')[2:]} :"
        )

        col1, col2 = st.columns(2)
        with col1:
            video_file = open(os.path.join(videodirectory, videoname), "rb")
            st.video(video_file, start_time=frame_num / fps)
        with col2:
            midi_path = os.path.join(mididirectory, newmidiname)
            trimmed_path = os.path.join(mididirectory, f"trimmed{tokeninfo[0]}.mid")
            rednoteindex = filter_midi_notes(midi_path, tokeninfo[0], trimmed_path)
            mid = stroll.MidiFile(trimmed_path)
            mid.draw_roll(rednoteidx=rednoteindex)
            os.remove(trimmed_path)

        st.write(f"Decided {st.session_state.index + 1} of {len(buttons)} undecided fingerings")
        st.write(f"Total frame: {tokeninfo[3]}")

        user_input = st.text_input(
            "If there are no right candidates, type the finger number from 1 to 10 (1-5: left, 6-10: right thumb~little).",
            key=f"{st.session_state.index}-input",
        )
        if st.button("User input", key=f"{st.session_state.index}-inputbutton"):
            st.session_state.history.append(st.session_state.index)
            st.session_state.responses.append([int(user_input), tokeninfo[0]])
            st.session_state.index += 1
            st.rerun()

        for button_name in buttons[st.session_state.index]:
            str_button_name = ""
            for idx, val in enumerate(button_name):
                strval = f"L{val}" if val <= 5 else f"R{val-5}"
                str_button_name += (strval if idx != len(button_name) - 1 else str(val)) + (" frames" if idx == len(button_name) - 1 else ": ")
            if st.button(str_button_name, key=f"{st.session_state.index}-{button_name[0]}"):
                button_click(button_name)
                break
    else:
        st.write("Completed all steps")

    # Complete handling
    if st.session_state.index >= len(buttons):
        if st.button("Complete"):
            responses = complete()
            st.write(f"Responses: {responses}")
            with open(FINGERING_TXT, "r") as f:
                fingering_textlist = f.read().strip().split("\n")
            with open(COMPLETE_FINGERING_TXT, "w") as complete_textfile:
                complete_textfile.write("Token number 1~5: Left hand, 6~10: Right hand (Both from thumb finger to little finger) \n")
                human_label_count = 0
                for i, line in enumerate(fingering_textlist):
                    if not line.strip():
                        continue
                    parts = line.split(",")
                    if len(parts) >= 2 and human_label_count < len(responses) - 1 and responses[human_label_count][1] == int(parts[0].strip()):
                        complete_textfile.write(f"Tokennumber={i}, Finger={responses[human_label_count][0]}, \n")
                        human_label_count += 1
                    else:
                        complete_textfile.write(f"Tokennumber={i}, Finger={parts[1].strip() if len(parts) > 1 else '?'}, \n")

    if st.session_state.history and st.button("Undo"):
        undo()
    if st.session_state.index >= len(buttons) and st.button("Reset"):
        reset()

    st.write(f"Current Index: {st.session_state.index}")
    st.write(f"Responses: {st.session_state.responses}")


def _decider(pressedfingerlist, undecidedtokeninfolist, fps, videoname, newmidiname):
    """Return final fingerinfo after manual review"""
    decision = _button_input(undecidedtokeninfolist, fps, videoname, newmidiname)
    if decision and len(decision) == len(undecidedtokeninfolist) + 1:
        for j in range(len(pressedfingerlist)):
            if pressedfingerlist[j] == "Noinfo" and decision[0][1] == j:
                pressedfingerlist[j] = decision[0][0]
                decision.pop(0)
    return pressedfingerlist


# -----------------------------------------------------------------------------
# 4. Page handlers (workflow order)
# -----------------------------------------------------------------------------
def intro():
    st.write("# FingeringDetection: Automated System for Detecting Fingering")
    st.sidebar.success("Select the menu above.")
    st.markdown("""
    **FingeringDetection** is a semi-automatic assistant to label fingering from video.
    The algorithm only asks confusing fingering for us, so you can answer from the video or skip if hard to determine.

    #### Prerequisites
    - Top-view video
    - Performance MIDI recorded from the above video

    #### Data format for PianoVAM
    - Audio: 16kHz wav format
    - MIDI: mid and Logic Project file
    - Video: Top-View 60fps 720×1280 (Full 88 keyboard must be shown.)

    **👈 Select a menu from the dropdown on the left**
    """)
    st.write("Settings (three dots at upper right) - use wide mode")


def keyboardcoordinate():
    """1. Specify keyboard corner coordinates"""
    st.sidebar.success("Select the menu above.")
    files = sorted([f for f in os.listdir(filepath) if f.endswith(".mp4")])
    selected_option = st.selectbox("Select video files:", files)

    video = cv2.VideoCapture(os.path.join(filepath, selected_option))
    ret, image = video.read()
    cv2.imwrite("tmp.jpg", image)
    value = streamlit_image_coordinates("tmp.jpg", key="local4", use_column_width="always", click_and_drag=True)
    st.write("Click leftupper, leftunder, rightupper, rightunder of the keyboard, then click the button.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("leftupper"):
            pickle.dump([value["x1"] / value["width"], value["y1"] / value["height"]], open(KEYBOARD_CORNER_PATHS["lu"], "wb"))
        if st.button("leftunder"):
            pickle.dump([value["x1"] / value["width"], value["y1"] / value["height"]], open(KEYBOARD_CORNER_PATHS["ld"], "wb"))
    with col2:
        if st.button("rightupper"):
            pickle.dump([value["x1"] / value["width"], value["y1"] / value["height"]], open(KEYBOARD_CORNER_PATHS["ru"], "wb"))
        if st.button("rightunder"):
            pickle.dump([value["x1"] / value["width"], value["y1"] / value["height"]], open(KEYBOARD_CORNER_PATHS["rd"], "wb"))

    if st.button("Complete"):
        lu = pickle.load(open(KEYBOARD_CORNER_PATHS["lu"], "rb"))
        ld = pickle.load(open(KEYBOARD_CORNER_PATHS["ld"], "rb"))
        ru = pickle.load(open(KEYBOARD_CORNER_PATHS["ru"], "rb"))
        rd = pickle.load(open(KEYBOARD_CORNER_PATHS["rd"], "rb"))
        if not os.path.exists(KEYBOARD_COORDINATE_PATH):
            pickle.dump({"Status": "Generated"}, open(KEYBOARD_COORDINATE_PATH, "wb"))
        keyboardcoordinateinfo = pickle.load(open(KEYBOARD_COORDINATE_PATH, "rb"))
        keyboardcoordinateinfo[selected_option[:-4]] = [lu, ru, ld, rd, 0.5, 0.0, 0.0, 0.0]
        pickle.dump(keyboardcoordinateinfo, open(KEYBOARD_COORDINATE_PATH, "wb"), pickle.HIGHEST_PROTOCOL)
    if value:
        st.write(value["x1"], value["y1"])


def keyboarddistortion():
    """2. Adjust keyboard distortion parameters"""
    st.sidebar.success("Select the menu above.")
    st.write("Adjust keyboard distortion parameters")
    files = sorted([f for f in os.listdir(filepath) if f.endswith(".mp4")])
    selected_option = st.selectbox("Select video files:", files)

    keyboardcoordinateinfo = pickle.load(open(KEYBOARD_COORDINATE_PATH, "rb"))
    if "blackratio" not in st.session_state:
        st.session_state["blackratio"] = keyboardcoordinateinfo[selected_option[:-4]][4]
    if "ldistortion" not in st.session_state:
        st.session_state["ldistortion"] = keyboardcoordinateinfo[selected_option[:-4]][5]
    if "rdistortion" not in st.session_state:
        st.session_state["rdistortion"] = keyboardcoordinateinfo[selected_option[:-4]][6]
    if "cdistortion" not in st.session_state:
        st.session_state["cdistortion"] = keyboardcoordinateinfo[selected_option[:-4]][7]

    video = cv2.VideoCapture(os.path.join(filepath, selected_option))
    ret, image = video.read()
    img_np = np.array(image)
    img = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_np)
    keyboard = generatekeyboard(
        lu=keyboardcoordinateinfo[selected_option[:-4]][0],
        ru=keyboardcoordinateinfo[selected_option[:-4]][1],
        ld=keyboardcoordinateinfo[selected_option[:-4]][2],
        rd=keyboardcoordinateinfo[selected_option[:-4]][3],
        blackratio=st.session_state["blackratio"],
        ldistortion=st.session_state["ldistortion"],
        rdistortion=st.session_state["rdistortion"],
        cdistortion=st.session_state["cdistortion"],
    )
    keyboard_image = cv2.cvtColor(draw_keyboard_on_image(img.numpy_view(), keyboard), cv2.COLOR_BGR2RGB)

    col1, col2 = st.columns(2)
    with col1:
        st.image(keyboard_image)
    with col2:
        st.session_state["blackratio"] = st.slider("Black/white key length ratio?", 0.0, 1.0, st.session_state["blackratio"], step=0.05)
        st.session_state["cdistortion"] = st.slider("E4-F4 point distortion?", -0.5, 0.5, st.session_state["cdistortion"] * 50) / 50
        st.session_state["ldistortion"] = st.slider("Left side distortion?", -0.3, 0.3, st.session_state["ldistortion"] * 2000) / 2000
        st.session_state["rdistortion"] = st.slider("Right side distortion?", -0.3, 0.3, st.session_state["rdistortion"] * 2000) / 2000

    if st.button("Save keyboard"):
        keyboardcoordinateinfo[selected_option[:-4]] = [
            keyboardcoordinateinfo[selected_option[:-4]][0],
            keyboardcoordinateinfo[selected_option[:-4]][1],
            keyboardcoordinateinfo[selected_option[:-4]][2],
            keyboardcoordinateinfo[selected_option[:-4]][3],
            st.session_state["blackratio"],
            st.session_state["ldistortion"],
            st.session_state["rdistortion"],
            st.session_state["cdistortion"],
        ]
        pickle.dump(keyboardcoordinateinfo, open(KEYBOARD_COORDINATE_PATH, "wb"), pickle.HIGHEST_PROTOCOL)
        st.write("Saved keyboard.")
    if st.button("Reload image"):
        st.rerun()


def preprocess():
    """3. Remove Logic Smart Tempo"""
    st.write("Delete smart tempo (Logic Pro)")
    files = sorted([f for f in os.listdir(mididirectory) if "_singletempo" not in str(f)])
    selected_option = st.selectbox("Select MIDI files:", files)
    st.write("Settings (three dots at upper right) - use wide mode")
    if st.button("Delete smart tempo"):
        delete_smart_tempo(os.path.join(mididirectory, selected_option))
        st.write(f"Changed {os.path.join(mididirectory, selected_option)}.")


def videodata():
    """4. Generate MediaPipe data"""
    st.sidebar.success("Select the menu above.")
    st.write("Generate MediaPipe hand data from video")
    files = sorted([f for f in os.listdir(filepath) if f.endswith(".mp4")])
    selected_option = st.selectbox("Select video files:", files)
    if st.button("Generate mediapipe data"):
        datagenerate(selected_option)
        st.write(f"Generated data of {filepath}/{selected_option}")


def prefinger():
    """5. Pre-finger labeling (auto-generate fingering candidates)"""
    st.write("# FingeringDetection: Automated System for Detecting Fingering")
    st.sidebar.success("Select the menu above.")
    files = sorted([f for f in os.listdir(mididirectory) if "_singletempo" in str(f)])
    selected_option = st.selectbox("Select MIDI files:", files)
    st.write("Settings (three dots at upper right) - use wide mode")

    newmidiname = selected_option
    videoname = "_".join(selected_option.split("_")[:-1]) + ".mp4"
    st.write("Selected MIDI:", selected_option)

    if st.button("Precorrespond fingering"):
        st.write("Fingering pre-labeling started")
        video = cv2.VideoCapture(os.path.join(filepath, videoname))
        if not video.isOpened():
            st.error("Failed to open video.")
            return
        frame_rate = get_video_fps(os.path.join(filepath, videoname))
        frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
        dirname = _get_mediapipe_dirname(videoname)

        with open(os.path.join(dirname, f"floatingframes_{videoname[:-4]}_{min_hand_detection_confidence*100}{min_hand_presence_confidence*100}{min_tracking_confidence*100}.pkl"), "rb") as f:
            floatingframes = pickle.load(f)
        with open(os.path.join(dirname, f"handlist_{videoname[:-4]}_{min_hand_detection_confidence*100}{min_hand_presence_confidence*100}{min_tracking_confidence*100}.pkl"), "rb") as f:
            handlist = pickle.load(f)
        keyboardcoordinateinfo = pickle.load(open(KEYBOARD_COORDINATE_PATH, "rb"))
        keyboard = generatekeyboard(
            lu=keyboardcoordinateinfo[videoname[:-4]][0],
            ru=keyboardcoordinateinfo[videoname[:-4]][1],
            ld=keyboardcoordinateinfo[videoname[:-4]][2],
            rd=keyboardcoordinateinfo[videoname[:-4]][3],
            blackratio=keyboardcoordinateinfo[videoname[:-4]][4],
            ldistortion=keyboardcoordinateinfo[videoname[:-4]][5],
            rdistortion=keyboardcoordinateinfo[videoname[:-4]][6],
            cdistortion=keyboardcoordinateinfo[videoname[:-4]][7],
        )

        handfingerpositionlist = []
        for handsinfo in stqdm(handlist, desc="Detecting finger position..."):
            handfingerpositionlist.append(handpositiondetector(handsinfo, floatingframes, keyboard))

        tokenlist = miditotoken(newmidiname[:-4], frame_rate, "simplified")
        prefingercorrespond = handfingercorresponder(
            tokentoframeinfo(tokenlist, frame_count), handfingerpositionlist, keyboard, tokenlist
        )
        fingerinfo, undecidedfingerlist = decide_fingering(tokenlist, prefingercorrespond)

        with open(FINGERING_TXT, "w") as f:
            for i in range(len(fingerinfo)):
                f.write(f"{i},{fingerinfo[i]}, \n")

        conf_str = f"{min_hand_detection_confidence*100}{min_hand_presence_confidence*100}{min_tracking_confidence*100}"
        with open(os.path.join(dirname, f"fingerinfo_{videoname}_{conf_str}.pkl"), "wb") as f:
            pickle.dump(fingerinfo, f)
        with open(os.path.join(dirname, f"undecidedfingerlist_{videoname}_{conf_str}.pkl"), "wb") as f:
            pickle.dump(undecidedfingerlist, f)
        st.write("Prefinger info saved")


def label():
    """6. Manual review (label undecided notes)"""
    initialize_state()
    st.write("# FingeringDetection: Automated System for Detecting Fingering")
    st.sidebar.success("Select the menu above.")
    files = sorted([f for f in os.listdir(mididirectory) if "_singletempo" in str(f)])
    selected_option = st.selectbox("Select MIDI files:", files)
    st.write("Settings (three dots at upper right) - use wide mode")

    newmidiname, videoname = _get_midiname_from_video(selected_option)
    st.write("Selected MIDI:", selected_option)
    frame_rate = get_video_fps(os.path.join(filepath, videoname))
    dirname = _get_mediapipe_dirname(videoname)
    conf_str = f"{min_hand_detection_confidence*100}{min_hand_presence_confidence*100}{min_tracking_confidence*100}"

    with open(os.path.join(dirname, f"fingerinfo_{videoname}_{conf_str}.pkl"), "rb") as f:
        fingerinfo = pickle.load(f)
    with open(os.path.join(dirname, f"undecidedfingerlist_{videoname}_{conf_str}.pkl"), "rb") as f:
        undecidedfingerlist = pickle.load(f)

    fingerinfo = _decider(fingerinfo, undecidedfingerlist, frame_rate, videoname, newmidiname)
    st.write(fingerinfo)


def annotate():
    """7. Ground truth manual annotation (first 150 notes)"""
    initialize_state()
    st.write("# FingeringDetection: Automated System for Detecting Fingering")
    st.sidebar.success("Select the menu above.")
    files = sorted([f for f in os.listdir(mididirectory) if "_singletempo" in f])
    selected_option = st.selectbox("Select MIDI files:", files)

    newmidiname, videoname = _get_midiname_from_video(selected_option)
    st.write("Selected MIDI:", selected_option)
    frame_rate = get_video_fps(os.path.join(filepath, videoname))
    tokeninfolist = miditotoken(newmidiname[:-4], frame_rate, "simplified")

    def notecount(path):
        mid = mido.MidiFile(path)
        return sum(1 for t in mid.tracks for msg in t if msg.type == "note_on")

    max_notes = min(150, notecount(os.path.join(mididirectory, newmidiname)))

    def button_click():
        if st.session_state.index < max_notes:
            st.session_state.history.append(st.session_state.index)
            st.session_state.responses += [int(x) for x in user_input.split(",")]
            st.session_state.index += len(user_input.split(","))
        st.rerun()

    def undo():
        if st.session_state.history:
            st.session_state.index -= 1
            st.session_state.responses.pop()
        st.rerun()

    def reset():
        st.session_state.index = 0
        st.session_state.history = []
        st.session_state.responses = []
        st.rerun()

    def complete():
        st.session_state.responses.append("Complete")
        return st.session_state.responses

    if st.session_state.index < max_notes:
        tokeninfo = tokeninfolist[st.session_state.index]
        st.write(
            f"#### Choose finger for {tokeninfo[1]}({pitch_list[tokeninfo[1]]}) at frame {tokeninfo[0]} "
            f"or time {str(int(tokeninfo[0]/frame_rate//60)).zfill(2)}:{str(math.floor(tokeninfo[0]/frame_rate%60)).zfill(2)}:"
        )
        col1, col2 = st.columns(2)
        with col1:
            video_file = open(os.path.join(videodirectory, videoname), "rb")
            st.video(video_file, start_time=math.floor(tokeninfo[0] / frame_rate))
        with col2:
            midi_path = os.path.join(mididirectory, newmidiname)
            trimmed_path = os.path.join(mididirectory, f"trimmed{st.session_state.index}.mid")
            rednoteindex = filter_midi_notes(midi_path, st.session_state.index, trimmed_path)
            mid = stroll.MidiFile(trimmed_path)
            mid.draw_roll(rednoteidx=rednoteindex)
            os.remove(trimmed_path)
        st.write(f"Decided {st.session_state.index} of {max_notes}")
        upcoming = [pitch_list[tokeninfolist[st.session_state.index + i][1]] for i in range(10) if st.session_state.index + i < max_notes]
        st.write(f"Present and upcoming notes: {upcoming}")
        user_input = st.text_input("Enter finger number 1-10, comma-separated for multiple")
        if st.button("next"):
            button_click()
    else:
        st.write("Completed all steps")

    if st.session_state.index >= max_notes:
        if st.button("Complete"):
            responses = complete()
            st.write(f"Responses: {responses}")
            out_path = os.path.join(_FINGERING_DIR, f"{newmidiname[:-16]}.txt")
            with open(out_path, "a") as f:
                f.write(", ".join(str(r) for r in responses) + ", ")

    if st.session_state.history and st.button("Undo"):
        undo()
    if st.session_state.index >= 150 and st.button("Reset"):
        reset()
    st.write(f"Current Index: {st.session_state.index}")
    st.write(f"Responses: {st.session_state.responses}")


# -----------------------------------------------------------------------------
# 5. Main: menu and routing
# -----------------------------------------------------------------------------
PAGE_ORDER = [
    ("Intro", intro),
    ("1. Keyboard detection", keyboardcoordinate),
    ("2. Keyboard distortion", keyboarddistortion),
    ("3. Delete smart tempo", preprocess),
    ("4. Generate MediaPipe data", videodata),
    ("5. Pre-finger labeling", prefinger),
    ("6. Label", label),
    ("7. Ground truth annotation", annotate),
]
page_names_to_funcs = dict(PAGE_ORDER)

demo_name = st.sidebar.selectbox("**MENU** 🍽️", page_names_to_funcs.keys())
page_names_to_funcs[demo_name]()
