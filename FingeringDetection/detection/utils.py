"""
Utility functions for MIDI and video processing
"""
import json
import os
import subprocess

import mido
import pretty_midi


def get_video_fps(video_path):
    """Extract video FPS using ffprobe"""
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate", "-of", "json", video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    data = json.loads(result.stdout.decode())
    return eval(data["streams"][0]["r_frame_rate"])


def delete_smart_tempo(midiname):
    """Remove Logic Smart Tempo: convert to single tempo"""
    if "_singletempo" not in midiname:
        midi_data = pretty_midi.PrettyMIDI(midiname, initial_tempo=120)
        midi_data.write(midiname[:-4] + "_singletempo.mid")


def filter_midi_notes(input_midi, target_note_index, output_path):
    """
    Extract only ±15 notes around target_note_index from MIDI.
    Returns: New index of target_note in the extracted MIDI
    """
    mid = mido.MidiFile(input_midi)
    target_note_new_index = -1
    new_mid = mido.MidiFile()
    new_mid.ticks_per_beat = mid.ticks_per_beat

    for track in mid.tracks:
        new_track = mido.MidiTrack()
        all_notes = [msg for msg in track if msg.type == "note_on"]
        start_index = max(0, target_note_index - 15)
        end_index = min(len(all_notes) - 1, target_note_index + 15)
        indices_to_keep = set(range(start_index, end_index + 1))
        active_notes = []
        current_note_index = 0
        new_note_index = 0

        for msg in track:
            if msg.type == "note_on" and msg.velocity > 0:
                if current_note_index in indices_to_keep:
                    new_track.append(msg)
                    active_notes.append(msg.note)
                    if current_note_index == target_note_index:
                        target_note_new_index = new_note_index
                    new_note_index += 1
                current_note_index += 1
            elif (msg.type == "note_on" and msg.velocity == 0) or msg.type == "note_off":
                if msg.note in active_notes:
                    if msg.type == "note_on" and msg.velocity == 0:
                        new_msg = mido.Message("note_off", channel=msg.channel, note=msg.note, velocity=0, time=msg.time)
                        new_track.append(new_msg)
                    else:
                        new_track.append(msg)
                    active_notes.remove(msg.note)
            else:
                if current_note_index in indices_to_keep:
                    new_track.append(msg)

        new_mid.tracks.append(new_track)

    new_mid.save(output_path)
    return target_note_new_index
