"""Assemble the S01E01 dialogue and time the visual beats for an animatic."""

import argparse
import json
import math
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

import numpy as np
import soundfile as sf

RATE = 24000
ROOT = Path(__file__).resolve().parents[1]
VOICES = {"Walter": ("am_michael", 0.92), "Kyle": ("am_fenrir", 1.07)}
HOLDS = {
    "setup": (1.4, "Kyle unveils the workstation", 1.7, "Walter studies the machine"),
    "escalation": (1.8, "Walter discovers the cat gallery", 1.4, "Walter lets Kyle’s pitch hang"),
    "punchline": (1.5, "Susan brings up the spreadsheet", 1.6, "Walter processes the numbers"),
    "outro": (1.2, "Walter finds the Generate button", 2.8, "The fans spin up over the kitten result"),
}


def pcm(path, options=()):
    data = subprocess.check_output([
        "ffmpeg", "-v", "error", "-i", str(path), *options,
        "-map", "0:a:0", "-ar", str(RATE), "-ac", "1", "-f", "f32le", "-",
    ])
    return np.frombuffer(data, dtype="<f4").copy()


def approved_takes():
    pilot = json.loads((ROOT / "episodes/walter-kyle-pilot.json").read_text(encoding="utf-8"))
    first, kyle, _ = pilot["timing"]
    kyle_start = kyle["speech_start"] - 0.12
    kyle_duration = kyle["speech_end"] - kyle_start + 0.18
    return {
        ("Walter", first["line"]): (
            pcm(ROOT / "walter-keynote-audition.wav"), "Approved Walter keynote take",
        ),
        ("Kyle", kyle["line"]): (
            pcm(ROOT / "walter-kyle-hair-fixed.mp4",
                ("-ss", str(kyle_start), "-t", str(kyle_duration))),
            "Kyle’s line from the approved pilot",
        ),
        ("Susan", "The cat account is our only source of revenue."): (
            pcm(ROOT / "susan-australian-marlo.wav"), "Approved Susan Marlo take",
        ),
    }


def synthesize(pipeline, speaker, line, temp):
    if speaker not in VOICES:
        raise ValueError(f"An approved recording is required for {speaker}: {line}")
    voice, speed = VOICES[speaker]
    segments = [result.audio.numpy() for result in pipeline(line, voice=voice, speed=speed)]
    audio = np.concatenate(segments)
    active = np.flatnonzero(np.abs(audio) > 0.005)
    if not len(active):
        raise ValueError(f"Kokoro produced silence for {speaker}: {line}")
    first = max(0, active[0] - round(RATE * 0.035))
    last = min(len(audio), active[-1] + round(RATE * 0.06))
    audio = audio[first:last].copy()
    fade = np.linspace(0, 1, 120)
    audio[:120] *= fade
    audio[-120:] *= fade[::-1]
    if speaker == "Walter":
        wav = temp / "walter.wav"
        sf.write(wav, audio, RATE, subtype="FLOAT")
        audio = pcm(wav, ("-af", "equalizer=f=3400:t=q:w=1:g=-2,volume=0.90"))
    return audio, f"Kokoro {voice}"


def collect_draft(episode, pipeline, temp):
    known = approved_takes()
    parts = []
    for scene in episode["scenes"]:
        beat = scene["beat"]
        lead, lead_action, tail, tail_action = HOLDS[beat]
        parts.append(compose_hold(beat, lead, lead_action))
        for index, turn in enumerate(scene["dialogue"]):
            speaker, line = turn["speaker"], turn["line"]
            take = known.get((speaker, line))
            audio, source = take if take is not None else synthesize(pipeline, speaker, line, temp)
            if not len(audio) or not np.isfinite(audio).all():
                raise ValueError(f"Invalid recording for {speaker}: {line}")
            parts.append(({"beat": beat, "speaker": speaker, "line": line, "source": source}, audio))
            if speaker == "Susan":
                parts.append(compose_hold(beat, 1.45, "Kyle perks up and Walter absorbs the reveal"))
            elif index < len(scene["dialogue"]) - 1:
                parts.append((None, np.zeros(round(0.32 * RATE), dtype=np.float32)))
        parts.append(compose_hold(beat, tail, tail_action))
    return parts


def compose_hold(beat, seconds, action):
    return {"beat": beat, "action": action}, np.zeros(round(seconds * RATE), dtype=np.float32)


def assemble(parts, minimum):
    deficit = max(0, math.ceil(minimum * RATE) - sum(len(audio) for _, audio in parts))
    holds = [index for index, (cue, _) in enumerate(parts) if cue and "action" in cue]
    share, extra = divmod(deficit, len(holds))
    for rank, index in enumerate(holds):
        cue, audio = parts[index]
        parts[index] = cue, np.pad(audio, (0, share + (rank < extra)))

    timeline = []
    position = 0
    for cue, audio in parts:
        end = position + len(audio)
        if cue:
            timeline.append({**cue, "start_sample": position, "end_sample": end,
                             "start_seconds": round(position / RATE, 3),
                             "end_seconds": round(end / RATE, 3)})
        position = end
    return np.concatenate([audio for _, audio in parts]), timeline


def main():
    from kokoro import KPipeline

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wav", type=Path)
    parser.add_argument("--timing", required=True, type=Path)
    args = parser.parse_args()
    for path in (args.wav, args.timing):
        if path.exists():
            parser.error(f"Output already exists: {path}")
    episode = json.loads((ROOT / "episodes/S01E01-draft.json").read_text(encoding="utf-8"))
    pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M", device="cpu")
    with TemporaryDirectory() as directory:
        parts = collect_draft(episode, pipeline, Path(directory))
        audio, timeline = assemble(parts, episode["minimum_seconds"])
        with args.wav.open("xb") as output:
            sf.write(output, audio, RATE, format="WAV", subtype="PCM_16")
    timing = {"episode": episode["episode"], "sample_rate": RATE, "audio_file": args.wav.name,
              "duration_seconds": len(audio) / RATE, "timeline": timeline}
    with args.timing.open("x", encoding="utf-8") as output:
        output.write(json.dumps(timing, ensure_ascii=False, indent=2) + "\n")
    print(f"{args.wav}: {timing['duration_seconds']:.2f} seconds")


if __name__ == "__main__":
    main()
