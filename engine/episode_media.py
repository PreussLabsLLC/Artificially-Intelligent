"""Shared voice and subtitle operations for episode production."""

import re
from textwrap import fill

from render_s01e01_final import SUBTITLES
from render_table_read import RATE, pcm
from render_walter import run


PIPER_MODEL = (
    "models--DataCraftsmanAustralia--piper-en_AU-librivox-medium/snapshots/"
    "7f35faf19fe1789ece4b14233448f7c04e35a84f/en_AU-librivox-medium.onnx"
)


def marlo(line, model, temp):
    text = temp / "susan.txt"
    wav = temp / "susan.wav"
    # Piper can mispronounce words adjacent to smart quotes. Keep contractions.
    speech = re.sub(r"‘(.+?)’(?!\w)", r"\1", line).replace("’", "'")
    text.write_text(speech + "\n", encoding="utf-8")
    run("uv", "run", "--no-project", "--with", "piper-tts==1.8.0", "python", "-m", "piper",
        "-m", str(model), "-s", "2", "--length-scale", "1.08", "-i", str(text), "-f", str(wav))
    return pcm(wav, ("-af", "volume=0.8",))


def stamp(samples):
    seconds, millis = divmod(round(1000 * samples / RATE), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"


def write_subtitles(episode, timeline, temp):
    speech = []
    for cue in timeline:
        if "speaker" not in cue:
            continue
        spoken = [shape for shape in cue.get("mouth_cues", ()) if shape["value"] != "X"]
        start, end = cue["start_sample"], cue["end_sample"]
        if spoken:
            end = min(end, start + round((spoken[-1]["end"] + 0.12) * RATE))
            start += round(spoken[0]["start"] * RATE)
        speech.append((start, end, cue))
    tracks = []
    for code, language, label in SUBTITLES:
        blocks = []
        for index, (start, end, cue) in enumerate(speech):
            line = fill(cue["line"], width=42) if code == "en" else cue[code]
            if index + 1 < len(speech):
                next_start = speech[index + 1][0]
                needed = round(len(line) * RATE / 20)
                end = max(end, min(start + needed, end + RATE // 2, next_start - RATE // 12))
            blocks.append(f"{len(blocks)+1}\n{stamp(start)} --> {stamp(end)}\n{line}")
        path = temp / f"{episode}.{code}.srt"
        path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
        tracks.append((path, language, label))
    return tracks
