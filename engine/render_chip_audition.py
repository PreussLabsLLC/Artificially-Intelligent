"""Render Chip's S01E02 voice and cutout audition."""

import argparse
import math
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import soundfile as sf

from render_animatic import lip_sync
from render_pilot import kyle
from render_table_read import RATE, pcm, synthesize
from render_walter import FPS, INK, OFFICE, run


KYLE_LINE = "Hey, Chip. Can I use the restroom?"
CHIP_LINE = "Request approved. As a contractor, please clock out first."


def synthesize_chip(pipeline, line, temp):
    audio = np.concatenate([
        segment.audio.numpy()
        for segment in pipeline(line, voice="am_onyx", speed=0.94)
    ])
    source = temp / "chip.wav"
    sf.write(source, audio, RATE, subtype="FLOAT")
    audio = pcm(source, ("-af", "highpass=f=210,lowpass=f=3400,tremolo=f=24:d=0.16,volume=1.1"))
    active = np.flatnonzero(np.abs(audio) > 0.005)
    if not len(active):
        raise ValueError(f"Chip's voice returned silence for {line!r}")
    return audio[max(0, active[0] - 960):active[-1] + 1441]


def chip(status, mouth, x=650):
    lamp = {"idle": "#793737", "thinking": "#ffb74f", "speaking": "#ff654e"}[status]
    mouth_height = {"X": 0, "A": 0, "B": 1, "C": 4, "D": 7,
                    "E": 5, "F": 5, "G": 3, "H": 4}[mouth]
    display = (f'<ellipse cx="0" cy="-93" rx="11" ry="{mouth_height}" fill="#57e3ed"/>'
               if mouth_height else '<path d="M-9 -96q9 8 18 0" fill="none" stroke="#57e3ed"/>')
    return f"""
<ellipse cx="{x}" cy="465" rx="77" ry="9" fill="#343941" opacity=".28"/>
<g transform="translate({x} 457) scale(1.23)" stroke="{INK}" stroke-width="3"
   stroke-linecap="round" stroke-linejoin="round">
  <rect x="-51" y="-24" width="102" height="25" rx="12" fill="#253451"/>
  <g fill="#7088a7">
    <circle cx="-32" cy="-11" r="7"/><circle cx="0" cy="-11" r="7"/>
    <circle cx="32" cy="-11" r="7"/>
  </g>
  <path d="M-33-62q-23 0-25 24m91-24q23 0 25 24" fill="none" stroke-width="12"/>
  <path d="M-33-62q-23 0-25 24m91-24q23 0 25 24" fill="none" stroke="#9da9b3" stroke-width="7"/>
  <path d="M-64-30q-3-13 6-13t8 12m100 0q-1-12 8-12t6 13" fill="none" stroke-width="5"/>
  <rect x="-36" y="-73" width="72" height="53" rx="13" fill="#f2edda"/>
  <rect x="-23" y="-60" width="46" height="23" rx="3" fill="#a9bdd0"/>
  <text x="0" y="-44" text-anchor="middle" font-family="sans-serif" font-weight="bold"
        font-size="13" stroke="none" fill="{INK}">CHIP</text>
  <path d="M0-134v-18" stroke-width="4"/>
  <circle cx="0" cy="-157" r="7" fill="{lamp}"/>
  <rect x="-54" y="-120" width="108" height="28" rx="12" fill="#bdc4be"/>
  <rect x="-48" y="-136" width="96" height="63" rx="22" fill="#f2edda"/>
  <rect x="-38" y="-127" width="76" height="45" rx="13" fill="#172b48"/>
  <path d="M-21-106q4-12 9 0m24 0q5-12 9 0" fill="none" stroke="#57e3ed" stroke-width="4"/>
  {display}
</g>"""


def mouth_at(cue, sample):
    local = (sample - cue["start_sample"]) / RATE
    return next((shape["value"] for shape in cue["mouth_cues"]
                 if shape["start"] <= local < shape["end"]), "X")


def record_audition(pipeline, temp):
    kyle_audio, _ = synthesize(pipeline, "Kyle", KYLE_LINE, temp)
    chip_audio = synthesize_chip(pipeline, CHIP_LINE, temp)
    kyle_start = round(0.4 * RATE)
    kyle_end = kyle_start + len(kyle_audio)
    chip_start = kyle_end + round(0.62 * RATE)
    chip_end = chip_start + len(chip_audio)
    frame_count = math.ceil((chip_end / RATE + 1.15) * FPS)
    samples = np.zeros(frame_count * RATE // FPS, dtype=np.float32)
    samples[kyle_start:kyle_end] = kyle_audio
    samples[chip_start:chip_end] = chip_audio
    cues = [
        {"speaker": "Kyle", "line": KYLE_LINE, "start_sample": kyle_start, "end_sample": kyle_end},
        {"speaker": "Chip", "line": CHIP_LINE, "start_sample": chip_start, "end_sample": chip_end},
    ]
    lip_sync(cues, samples, RATE, temp)
    return samples, cues


def audition_layers(cues, frame_count):
    kyle_cue, chip_cue = cues
    kyle_start, kyle_end = kyle_cue["start_sample"], kyle_cue["end_sample"]
    chip_start, chip_end = chip_cue["start_sample"], chip_cue["end_sample"]
    for index in range(frame_count):
        sample = index * RATE // FPS
        kyle_mouth, chip_mouth = (mouth_at(cue, sample) for cue in cues)
        status = "idle"
        if kyle_end <= sample < chip_start:
            status = "thinking"
        elif chip_mouth != "X":
            status = "speaking"
        if kyle_start <= sample < kyle_end:
            reaction = ("present", 0.35)
        elif chip_end + 7200 <= sample < chip_end + 10080:
            reaction = ("blink", 1)
        elif sample >= chip_end:
            reaction = ("raise_brow", 0.65)
        else:
            reaction = ("raise_brow", 0)
        state = (kyle_mouth, reaction, status, chip_mouth)
        yield state, [OFFICE, kyle(kyle_mouth, *reaction, x=365), chip(status, chip_mouth)]


def main():
    from kokoro import KPipeline

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"Output already exists: {args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)

    pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M", device="cpu")
    with TemporaryDirectory() as folder:
        temp = Path(folder)
        samples, cues = record_audition(pipeline, temp)
        frame_count = len(samples) * FPS // RATE
        wav = temp / "mix.wav"
        sf.write(wav, samples, RATE, subtype="PCM_16")
        cache = {}
        for index, (state, parts) in enumerate(audition_layers(cues, frame_count)):
            frame = temp / f"frame-{index:04}.png"
            if state in cache:
                frame.hardlink_to(cache[state])
                continue
            svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540">'
                   + "".join(parts) + "</svg>")
            run("rsvg-convert", "-w", "1920", "-h", "1080", "-o", str(frame), input=svg.encode())
            cache[state] = frame
        run("ffmpeg", "-v", "error", "-n", "-framerate", str(FPS), "-i", str(temp / "frame-%04d.png"),
            "-i", str(wav), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            "-movflags", "+faststart", str(args.output))
        print(f"{args.output}: {frame_count / FPS:.2f}s, "
              f"mouth cues {[len(cue['mouth_cues']) for cue in cues]}")


if __name__ == "__main__":
    main()
