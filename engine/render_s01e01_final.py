"""Render S01E01 with the approved music mix and selectable subtitles."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
TIMING = ROOT / "episodes/S01E01-animatic-timing.json"
CUES = ROOT / "episodes/S01E01-animatic-cues.json"
OUTPUT = ROOT / "output/S01E01-Return-On-Investment.mp4"
MUSIC = {
    "intro": ("5df9b4bb-83e1-280d-5a4b-06d109331703.mp3",
              "0a1a1dbd102e9e7fb38b3d002501820078c786114f8584f05e7a24235a62acc1"),
    "outro": ("a47ad749-1a67-a443-67c9-295f7f3b6ed7.mp3",
              "a81b3c051c8e85a1964db127b23feeac25ddd890d2fea936050936f35a6427e5"),
    "bed": ("ba258e7a-3803-e432-6d04-133a12632004.mp3",
            "a59f5f39c9622ed27f84464d5b60be553951b59eb4eec28f95c6de07c53e07b9"),
}
RATE = 48000
SUBTITLES = (
    ("en", "eng", "English"),
    ("de", "deu", "Deutsch"),
    ("es", "spa", "Español (Latinoamérica)"),
)


def checked_input(path, expected):
    if not path.is_file():
        raise FileNotFoundError(f"Restore the approved local audio file at {path}")
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError(f"Audio does not match the approved take at {path}")
    return path


def smooth(values):
    values = np.clip(values, 0, 1)
    return values * values * (3 - 2 * values)


def music_bed(source, timing):
    raw = subprocess.check_output([
        "ffmpeg", "-v", "error", "-i", str(source), "-t", "8.46",
        "-ar", str(RATE), "-ac", "2", "-f", "f32le", "-",
    ])
    riff = np.frombuffer(raw, dtype="<f4").reshape(-1, 2)
    overlap = round(0.06 * RATE)
    period = len(riff) - overlap
    loop = riff[:period].copy()
    blend = np.arange(overlap)[:, None] / overlap
    loop[:overlap] = riff[period:] * (1 - blend) + riff[:overlap] * blend

    duration = timing["duration_seconds"]
    length = round(duration * RATE)
    gains = np.full(length, 0.32, dtype=np.float32)
    attack, hold, release = (round(seconds * RATE) for seconds in (0.55, 0.28, 0.95))
    for cue in timing["timeline"]:
        if "speaker" not in cue:
            continue
        start = round(cue["start_sample"] * RATE / timing["sample_rate"])
        release_start = round(cue["end_sample"] * RATE / timing["sample_rate"]) + hold
        first = max(0, start - attack)
        last = min(length, release_start + release)
        indexes = np.arange(first, last)
        activity = smooth(np.minimum((indexes - start + attack) / attack,
                                     (release_start + release - indexes) / release))
        gains[first:last] = np.minimum(gains[first:last], 0.32 - 0.285 * activity)

    indexes = np.arange(length)
    seconds = indexes / RATE
    fan_start = timing["timeline"][-1]["start_seconds"]
    edge = smooth((seconds - 2) / 0.4) * smooth((fan_start - seconds) / 0.35)
    gains = (0.035 + (gains - 0.035) * edge) * smooth(seconds / 0.25)
    gains *= smooth((duration - seconds) / 0.5)
    return (loop[indexes % period] * gains[:, None]).astype("<f4").tobytes()


def mix(picture, tracks, timing, subtitles, output, temp):
    intermediate = temp / "intro-outro.m4a"
    bookends = (
        "[0:a]aresample=48000,pan=stereo|c0=c0|c1=c0[show];"
        "[1:a]aresample=48000,atrim=duration=10,asetpts=PTS-STARTPTS,"
        "volume='if(lt(t,1.7),0.63,if(lt(t,2.15),0.63-0.55*(t-1.7)/0.45,0.08))':eval=frame,"
        "afade=t=out:st=9:d=1[intro];"
        "[2:a]aresample=48000,atrim=duration=10,asetpts=PTS-STARTPTS,"
        "volume='if(lt(t,6.45),0.10,if(lt(t,7.05),0.10+0.90*(t-6.45)/0.60,1))':eval=frame,"
        "afade=t=in:st=0:d=0.35,afade=t=out:st=9.85:d=0.15,adelay=50000:all=1[outro];"
        "[show][intro][outro]amix=inputs=3:duration=first:normalize=0,"
        "alimiter=limit=0.97:level=false:latency=true,atrim=duration=60[mix]"
    )
    subprocess.run([
        "ffmpeg", "-v", "error", "-n", "-i", str(picture), "-i", str(tracks["intro"]),
        "-i", str(tracks["outro"]), "-filter_complex", bookends, "-map", "[mix]",
        "-c:a", "aac", "-b:a", "192k", str(intermediate),
    ], check=True)
    subtitle_inputs = []
    subtitle_maps = []
    for index, (path, language, label) in enumerate(subtitles):
        subtitle_inputs.extend(("-i", str(path)))
        subtitle_maps.extend((
            "-map", f"{index + 3}:s:0",
            f"-metadata:s:s:{index}", f"language={language}",
            f"-metadata:s:s:{index}", f"handler_name={label}",
            f"-disposition:s:{index}", "default" if index == 0 else "0",
        ))

    subprocess.run([
        "ffmpeg", "-v", "error", "-n", "-i", str(picture), "-i", str(intermediate),
        "-f", "f32le", "-ar", str(RATE), "-ac", "2", "-i", "-",
        *subtitle_inputs,
        "-filter_complex", "[1:a][2:a]amix=inputs=2:duration=first:normalize=0,"
        "alimiter=limit=0.98:level=false:latency=true,atrim=duration=60[mix]",
        "-map", "0:v:0", "-map", "[mix]", *subtitle_maps,
        "-c:v", "copy", "-c:a", "aac", "-c:s", "mov_text",
        "-b:a", "192k", "-movflags", "+faststart", str(output),
    ], input=music_bed(tracks["bed"], timing), check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error(f"Output already exists: {output}")

    timing = json.loads(TIMING.read_bytes())
    cues = json.loads(CUES.read_bytes())
    try:
        dialogue = checked_input(ROOT / timing["audio_file"], cues["audio_sha256"])
        tracks = {role: checked_input(ROOT / "assets/music" / name, digest)
                  for role, (name, digest) in MUSIC.items()}
    except (ValueError, FileNotFoundError) as error:
        parser.error(str(error))

    subtitles = [(ROOT / f"episodes/subtitles/S01E01.{code}.srt", language, label)
                 for code, language, label in SUBTITLES]
    for path, _, _ in subtitles:
        if not path.is_file():
            parser.error(f"Subtitle file is missing: {path}")

    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory() as folder:
        temp = Path(folder)
        picture = temp / "animatic.mp4"
        subprocess.run([
            sys.executable, str(ROOT / "engine/render_animatic.py"),
            str(dialogue), str(TIMING), str(picture), "--cues", str(CUES),
        ], cwd=ROOT, check=True)
        mix(picture, tracks, timing, subtitles, output, temp)
    print(output)


if __name__ == "__main__":
    main()
