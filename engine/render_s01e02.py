"""Produce Chief Executive Algorithm from the scene draft and approved Chip audition."""

import argparse
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.sax.saxutils import escape

import numpy as np
import soundfile as sf

from episode_media import PIPER_MODEL, marlo, write_subtitles
from render_animatic import lip_sync
from render_chip_audition import CHIP_LINE, KYLE_LINE, chip, mouth_at, synthesize_chip
from render_pilot import kyle
from render_s01e01_final import MUSIC, ROOT, checked_input, mix
from render_susan import susan
from render_table_read import RATE, assemble, compose_hold, pcm, synthesize
from render_walter import FPS, OFFICE, run, walter


EPISODE = "S01E02"
DRAFT = ROOT / "episodes" / f"{EPISODE}-draft.json"
CLIP = ROOT / "review" / f"{EPISODE}-Chip-audition.mp4"
OUTPUT = ROOT / "output" / f"{EPISODE}-Chief-Executive-Algorithm.mp4"
SCREEN = {
    "org": ("Organization chart", "Kyle", "CHIEF EXECUTIVE OFFICER", "#486b62"),
    "scan": ("Organization chart", "Review in progress", "CHECKING MANAGEMENT", "#8a6939"),
    "removed": ("Organization chart", "CEO role removed", "MANAGEMENT: −1", "#a74f49"),
    "ceo": ("Organization chart", "Chip", "CHIEF EXECUTIVE OFFICER", "#486b62"),
    "contractor": ("Personnel", "Kyle", "CONTRACTOR", "#8a6939"),
    "profit": ("Quarterly forecast", "Profit ×3", "PROJECTED", "#486b62"),
    "salary": ("Quarterly forecast", "Kyle’s salary: $0", "SAVINGS", "#486b62"),
}
REVEALS = {"removed": (2.0, "scan"), "ceo": (1.2, "removed"),
           "contractor": (2.0, "ceo"), "profit": (1.5, "ceo"), "salary": (1.3, "profit")}


def record(draft, pipeline, model, temp, minimum):
    parts = []
    for scene in draft["scenes"][:-1]:
        beat = scene["beat"]
        turns = scene["dialogue"]
        lead, pause = compose_hold(beat, scene["lead_seconds"], "opening hold")
        screen = parts[-1][0]["screen"] if parts else turns[0]["screen"]
        parts.append(({**lead, "screen": screen}, pause))
        for index, turn in enumerate(turns):
            speaker, line = turn["speaker"], turn["line"]
            if speaker == "Chip":
                take = synthesize_chip(pipeline, line, temp)
            elif speaker == "Susan":
                take = marlo(line, model, temp)
            else:
                take, _ = synthesize(pipeline, speaker, line, temp)
            if not len(take) or not np.isfinite(take).all():
                raise ValueError(f"Invalid recording from {speaker}")
            cue = {**turn, "beat": beat}
            parts.append((cue, take))
            if index + 1 < len(turns):
                parts.append((None, np.zeros(round(0.32 * RATE), dtype=np.float32)))
        tail, pause = compose_hold(beat, scene["tail_seconds"], "reaction hold")
        parts.append(({**tail, "screen": turns[-1]["screen"]}, pause))
    return assemble(parts, minimum)


def monitor(screen, y):
    title, body, label, color = SCREEN[screen]
    return f"""
<rect x="684" y="72" width="208" height="139" fill="#a9b3ad"/>
<g transform="translate(687 {y})" font-family="sans-serif" fill="#354940">
  <rect width="204" height="134" rx="5" fill="#576b65"/>
  <rect x="5" y="6" width="194" height="121" rx="2" fill="#edf0e3"/>
  <text x="17" y="28" font-size="15" font-weight="bold">{escape(title)}</text>
  <path d="M17 35h170" stroke="#a6b4a7"/>
  <text x="17" y="67" font-size="15" font-weight="bold" fill="{color}">{escape(body)}</text>
  <text x="17" y="91" font-size="11">{escape(label)}</text>
</g>"""


def render_frames(timeline, frame_count, temp, title):
    cache = {}
    cue_index = 0
    for index in range(frame_count):
        sample = index * RATE // FPS
        while cue_index + 1 < len(timeline) and sample >= timeline[cue_index + 1]["start_sample"]:
            cue_index += 1
        cue = timeline[cue_index]
        speaker = cue.get("speaker") if sample < cue["end_sample"] else None
        mouth = mouth_at(cue, sample) if speaker else "X"
        beat = cue["beat"]
        screen = cue["screen"]
        age = (sample - cue["start_sample"]) / RATE
        first_speech = cue_index == 0 or timeline[cue_index - 1]["screen"] != screen
        if speaker and first_speech and screen in REVEALS:
            delay, previous = REVEALS[screen]
            if age < delay:
                screen = previous
        blink = index % 108 in (0, 1, 2)
        chip_status = "speaking" if speaker == "Chip" and mouth != "X" else "idle"
        if screen == "scan" and chip_status == "idle":
            chip_status = "thinking"
        kyle_action = ("present", 0.32) if speaker == "Kyle" else (
            ("blink", 1) if blink else ("raise_brow", 0.65 if beat == "escalation" else 0))
        pose = (0, 0.52 if speaker == "Walter" else 0, 0, 0, blink and speaker != "Walter")
        opening = index < 48
        state = (speaker, mouth, blink, beat, screen, chip_status, opening)
        frame = temp / f"frame-{index:05}.png"
        if state in cache:
            frame.hardlink_to(cache[state])
            continue
        parts = [OFFICE, monitor(screen, 38 if beat == "punchline" else 73),
                 walter(mouth if speaker == "Walter" else "X", pose, x=171),
                 kyle(mouth if speaker == "Kyle" else "X", *kyle_action, x=366),
                 chip(chip_status, mouth if speaker == "Chip" else "X")]
        if beat == "punchline":
            parts.append(susan(mouth if speaker == "Susan" else "X", 0.78, blink, x=814))
        if opening:
            parts.append(f'<text x="480" y="507" text-anchor="middle" font-family="sans-serif" '
                         f'font-size="20" font-weight="bold" fill="#fff6dc">{escape(title)}</text>')
        svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540">' + "".join(parts) + "</svg>"
        run("rsvg-convert", "-w", "1920", "-h", "1080", "-o", str(frame), input=svg.encode())
        cache[state] = frame


def main():
    from kokoro import KPipeline

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--piper-model", type=Path, default=Path("/cache/huggingface/hub") / PIPER_MODEL)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"Output already exists: {args.output}")
    if not CLIP.is_file() or not args.piper_model.is_file():
        parser.error("The approved Chip audition and Susan’s Piper model must be available locally.")
    draft = json.loads(DRAFT.read_bytes())
    outro = draft["scenes"][-1]["dialogue"]
    if [turn["line"] for turn in outro] != [KYLE_LINE, CHIP_LINE]:
        parser.error("The outro dialogue must match the approved Chip audition.")
    tracks = {role: checked_input(ROOT / "assets/music" / name, digest)
              for role, (name, digest) in MUSIC.items()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M", device="cpu")
    with TemporaryDirectory() as folder:
        temp = Path(folder)
        audition = pcm(CLIP)
        frame_samples = RATE // FPS
        outro_frames = 172
        outro_samples = outro_frames * frame_samples
        if len(audition) < outro_samples:
            raise ValueError("Approved audition is shorter than its 172-frame picture")
        audio, timeline = record(draft, pipeline, args.piper_model, temp,
                                 draft["minimum_seconds"] - outro_samples / RATE)
        lip_sync(timeline, audio, RATE, temp)
        frame_count = math.ceil(len(audio) / frame_samples)
        outro_start = frame_count * frame_samples
        audio = np.concatenate((np.pad(audio, (0, outro_start - len(audio))), audition[:outro_samples]))
        render_frames(timeline, frame_count, temp, draft["title"])
        run("ffmpeg", "-v", "error", "-i", str(CLIP), "-map", "0:v:0",
            "-start_number", str(frame_count), str(temp / "frame-%05d.png"))

        # Speech ranges measured in the approved clip and relative to its first frame.
        for turn, (start, end) in zip(outro, ((0.445, 2.02), (2.675, 6.05))):
            timeline.append({**turn, "start_sample": outro_start + round(start * RATE),
                             "end_sample": outro_start + round(end * RATE)})
        last_line = timeline[-1]["end_sample"] / RATE
        duration = len(audio) / RATE
        timeline.append({"start_seconds": last_line})
        timing = {"duration_seconds": duration, "sample_rate": RATE, "timeline": timeline}
        wav = temp / "dialogue.wav"
        sf.write(wav, audio, RATE, subtype="PCM_16")
        picture = temp / "animatic.mp4"
        run("ffmpeg", "-v", "error", "-framerate", str(FPS), "-i", str(temp / "frame-%05d.png"),
            "-i", str(wav), "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", str(picture))
        subtitles = write_subtitles(EPISODE, timeline, temp)
        mix(picture, tracks, timing, subtitles, args.output, temp,
            outro_rise=round(last_line - (duration - 10), 3))
        if args.output.resolve() == OUTPUT:
            subtitle_dir = ROOT / "episodes/subtitles"
            subtitle_dir.mkdir(exist_ok=True)
            for path, _, _ in subtitles:
                (subtitle_dir / path.name).write_bytes(path.read_bytes())
        print(f"{args.output}: {duration:.3f}s, {frame_count + outro_frames} frames")


if __name__ == "__main__":
    main()
