"""Render an episode from a scene plan using the recurring cast and office set."""

import argparse
import json
import math
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from xml.sax.saxutils import escape

import numpy as np
import soundfile as sf

from episode_media import PIPER_MODEL, marlo, write_subtitles
from render_animatic import lip_sync
from render_chip_audition import chip, mouth_at, synthesize_chip
from render_pilot import kyle
from render_s01e01_final import MUSIC, ROOT, checked_input, mix
from render_susan import susan
from render_table_read import RATE, assemble, compose_hold, synthesize
from render_walter import FPS, OFFICE, run, walter
from scene_plan import OFFICE as OFFICE_SET, read_plan


SETS = {OFFICE_SET: OFFICE}


def voice(line, speaker, pipeline, model, temp):
    if speaker == "Chip":
        return synthesize_chip(pipeline, line, temp)
    if speaker == "Susan":
        return marlo(line, model, temp)
    take, _ = synthesize(pipeline, speaker, line, temp)
    return take


def record(plan, pipeline, model, temp):
    parts = []
    for index, scene in enumerate(plan["scenes"]):
        card = scene["card"]
        lead, pause = compose_hold(str(index), scene["lead_seconds"], "opening hold")
        parts.append(({**lead, "scene": index, "card": card}, pause))
        for turn in scene["dialogue"]:
            take = voice(turn["line"], turn["speaker"], pipeline, model, temp)
            if not len(take) or not np.isfinite(take).all():
                raise ValueError(f"Invalid recording from {turn['speaker']}")
            screen = turn.get("screen")
            if screen and screen["after"] >= len(take) / RATE:
                raise ValueError(f"Screen reveal falls after the line {turn['line']!r}")
            parts.append(({**turn, "scene": index, "card": card}, take))
            if screen:
                card = screen["card"]
            parts.append((None, np.zeros(round(0.32 * RATE), dtype=np.float32)))
        tail, pause = compose_hold(str(index), scene["tail_seconds"], "reaction hold")
        parts.append(({**tail, "scene": index, "card": card}, pause))
        print(f"Recorded scene {index + 1} of {len(plan['scenes'])}", flush=True)
    return assemble(parts, plan["minimum_seconds"])


def monitor(card):
    title, body, label = map(escape, card)
    return f"""
<rect x="684" y="72" width="208" height="139" fill="#a9b3ad"/>
<g transform="translate(687 38)" font-family="sans-serif" fill="#354940">
  <rect width="204" height="134" rx="5" fill="#576b65"/>
  <rect x="5" y="6" width="194" height="121" rx="2" fill="#edf0e3"/>
  <text x="17" y="28" font-size="14" font-weight="bold">{title}</text>
  <path d="M17 35h170" stroke="#a6b4a7"/>
  <text x="17" y="67" font-size="14" font-weight="bold" fill="#486b62">{body}</text>
  <text x="17" y="91" font-size="10">{label}</text>
</g>"""


def actors(cast, speaker, mouth, acting, blink):
    parts = []
    for name, x in cast.items():
        shape = mouth if speaker == name else "X"
        action = acting.get(name)
        if name == "Walter":
            pose = (0, 0.65 if action == "raise_brow" else 0,
                    0.52 if action == "gesture" else 0, 0.72 if action == "stare" else 0,
                    blink and speaker != name)
            parts.append(walter(shape, pose, x=x))
        elif name == "Kyle":
            mode, amount = ("blink", 1) if blink and speaker != name else (action or "raise_brow", 0.55 if action else 0)
            parts.append(kyle(shape, mode, amount, x=x))
        elif name == "Susan":
            parts.append(susan(shape, 0.76 if action == "present" else 0, blink and speaker != name, x=x))
        else:
            status = "speaking" if speaker == name and shape != "X" else (
                "thinking" if action == "thinking" else "idle")
            parts.append(chip(status, shape, x=x))
    return "".join(parts)


def frame_states(timeline, frame_count):
    cue_index = 0
    for index in range(frame_count):
        sample = index * RATE // FPS
        while cue_index + 1 < len(timeline) and sample >= timeline[cue_index + 1]["start_sample"]:
            cue_index += 1
        cue = timeline[cue_index]
        speaker = cue.get("speaker") if sample < cue["end_sample"] else None
        mouth = mouth_at(cue, sample) if speaker else "X"
        screen = cue.get("screen")
        age = (sample - cue["start_sample"]) / RATE
        card = screen["card"] if screen and age >= screen["after"] else cue["card"]
        acting = cue.get("acting", {})
        blink = index % 108 in (21, 22, 23)
        title = index < 48
        yield (cue["scene"], speaker, mouth, card, tuple(sorted(acting.items())), blink, title)


def title_layer(title):
    return ('<text x="480" y="507" text-anchor="middle" font-family="sans-serif" '
            f'font-size="20" font-weight="bold" fill="#fff6dc">{escape(title)}</text>')


def render_frames(plan, timeline, frame_count, temp):
    cache = {}
    for index, state in enumerate(frame_states(timeline, frame_count)):
        scene_index, speaker, mouth, card, acting, blink, title = state
        frame = temp / f"frame-{index:05}.png"
        if state in cache:
            frame.hardlink_to(cache[state])
            continue
        scene = plan["scenes"][scene_index]
        layers = [SETS[scene["set"]], monitor(plan["cards"][card]),
                  actors(scene["cast"], speaker, mouth, dict(acting), blink)]
        if title:
            layers.append(title_layer(plan["title"]))
        svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540">' + "".join(layers) + "</svg>"
        run("rsvg-convert", "-w", "1920", "-h", "1080", "-o", str(frame), input=svg.encode())
        cache[state] = frame
    print(f"Rendered {len(cache)} unique frames", flush=True)


def prepare_audio(plan, pipeline, model, temp, check_dialogue):
    audio, timeline = record(plan, pipeline, model, temp)
    wav = temp / "dialogue.wav"
    if check_dialogue:
        sf.write(wav, audio, RATE, subtype="PCM_16")
        timing_file = temp / "dialogue.json"
        timing_file.write_text(json.dumps({"sample_rate": RATE, "timeline": timeline}), encoding="utf-8")
        run("uv", "run", "--no-project", "--with", "faster-whisper==1.2.1", "python",
            str(Path(__file__).with_name("check_dialogue.py")), str(wav), str(timing_file))
    lip_sync(timeline, audio, RATE, temp)
    frame_samples = RATE // FPS
    frame_count = math.ceil(len(audio) / frame_samples)
    audio = np.pad(audio, (0, frame_count * frame_samples - len(audio)))
    timing = {"duration_seconds": len(audio) / RATE, "sample_rate": RATE, "timeline": timeline}
    sf.write(wav, audio, RATE, subtype="PCM_16")
    return wav, timing, frame_count


def main():
    from kokoro import KPipeline

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--piper-model", type=Path, default=Path("/cache/huggingface/hub") / PIPER_MODEL)
    parser.add_argument("--check-dialogue", action=argparse.BooleanOptionalAction, default=True,
                        help="Flag possible dialogue errors before rendering (default: enabled)")
    args = parser.parse_args()
    try:
        plan = read_plan(args.plan)
        tracks = {role: checked_input(ROOT / "assets/music" / name, digest)
                  for role, (name, digest) in MUSIC.items()}
    except (KeyError, ValueError, OSError) as error:
        parser.error(str(error))
    name = re.sub(r"[^A-Za-z0-9]+", "-", plan["title"]).strip("-")
    standard = ROOT / "output" / f"{plan['episode']}-{name}.mp4"
    output = (args.output or standard).resolve()
    if output.exists():
        parser.error(f"Output already exists: {output}")
    if any("Susan" in scene["cast"] for scene in plan["scenes"]) and not args.piper_model.is_file():
        parser.error("Susan’s Piper model must be available locally.")
    output.parent.mkdir(parents=True, exist_ok=True)

    pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M", device="cpu")
    with TemporaryDirectory() as folder:
        temp = Path(folder)
        wav, timing, frame_count = prepare_audio(plan, pipeline, args.piper_model, temp, args.check_dialogue)
        timeline = timing["timeline"]
        duration = timing["duration_seconds"]
        render_frames(plan, timeline, frame_count, temp)
        picture = temp / "picture.mp4"
        run("ffmpeg", "-v", "error", "-framerate", str(FPS), "-i", str(temp / "frame-%05d.png"),
            "-i", str(wav), "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", str(picture))
        subtitles = write_subtitles(plan["episode"], timeline, temp)
        last_line = next(cue["end_sample"] / RATE for cue in reversed(timeline) if "speaker" in cue)
        mix(picture, tracks, timing, subtitles, output, temp, outro_rise=round(last_line - duration + 10, 3))
        if output == standard:
            subtitle_dir = ROOT / "episodes/subtitles"
            subtitle_dir.mkdir(exist_ok=True)
            for path, _, _ in subtitles:
                (subtitle_dir / path.name).write_bytes(path.read_bytes())
        print(f"{output}: {duration:.3f}s, {frame_count} frames")


if __name__ == "__main__":
    main()
