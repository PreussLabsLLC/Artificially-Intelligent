"""Render the four S01E01 beats against the approved animatic audio."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import soundfile as sf

from render_pilot import kyle
from render_susan import susan
from render_walter import FPS, INK, OFFICE, run, walter

SPEAKERS = ("Walter", "Kyle", "Susan")


def lip_sync(timeline, samples, rate, temp):
    for index, cue in enumerate(timeline):
        if "speaker" not in cue:
            continue
        wav, transcript, output = (temp / f"{index}.{ext}" for ext in ("wav", "txt", "json"))
        sf.write(wav, samples[cue["start_sample"]:cue["end_sample"]], rate, subtype="PCM_16")
        transcript.write_text(cue["line"], encoding="utf-8")
        run("rhubarb", "-q", "-f", "json", "-d", str(transcript), "-o", str(output), str(wav))
        cue["mouth_cues"] = json.loads(output.read_text(encoding="utf-8"))["mouthCues"]
        if all(mouth["value"] == "X" for mouth in cue["mouth_cues"]):
            raise ValueError(f"Rhubarb found no speech in {cue['line']!r}")


def tower(light_phase):
    lamps = "".join(
        f'<rect x="93" y="{y}" width="54" height="5" rx="2" '
        f'fill="{"#55766c" if index == light_phase else "#8cd09c"}"/>'
        for index, y in enumerate((305, 319, 333, 347))
    )
    return f"""
<ellipse cx="129" cy="453" rx="65" ry="10" fill="#343941" opacity=".25"/>
<g stroke="{INK}" stroke-width="3" stroke-linejoin="round">
  <path d="M78 282l23-18h83v168l-22 18H78Z" fill="#454d57"/>
  <path d="M78 282h84v168H78Zm84 0 22-18" fill="#343740"/>
  <path d="M174 289v125" stroke="#68717b"/>
  <circle cx="120" cy="392" r="23" fill="#232932"/>
  <circle cx="120" cy="392" r="16" fill="#616a76"/>
  <circle cx="120" cy="392" r="5" fill="#343740"/>
  <path d="M120 376v10m0 12v10m-16-16h10m12 0h10" stroke="#343740"/>
</g>{lamps}"""


def cat_tile(x, y, color):
    return f"""
<g transform="translate({x} {y})">
  <rect width="48" height="28" rx="3" fill="#d4d9cd"/>
  <path d="M12 14l1-10 9 5h5l8-5 1 10q3 10-12 10T12 14" fill="{color}" stroke="#554e4b"/>
  <path d="M18 15h2m8 0h2m-7 4h2" stroke="#554e4b" stroke-linecap="round"/>
</g>"""


def monitor(beat, reveal, result):
    header = {
        "setup": "Workstation",
        "escalation": "Generated images",
        "punchline": "Revenue",
        "outro": "Generate kittens",
    }[beat]
    if beat == "setup":
        body = '<text x="18" y="59">4 GPUs online</text><path d="M18 72h163" stroke="#88ad98" stroke-width="5"/>'
    elif beat == "escalation":
        tiles = "".join(cat_tile(17 + index % 3 * 57, 39 + index // 3 * 32, color)
                        for index, color in enumerate(("#bc926b", "#b2a8aa", "#928c83",
                                                      "#e0be91", "#a9ad9b", "#be927e")))
        body = tiles
    elif beat == "punchline" and reveal:
        body = ('<text x="18" y="59">Cat account</text>'
                '<text x="182" y="59" text-anchor="end" font-weight="bold">100%</text>'
                '<path d="M18 70h164" stroke="#88ad98" stroke-width="3"/>')
    elif beat == "punchline":
        body = '<path d="M18 53h164m-164 13h164m-164 13h164M70 42v43m55-43v43" fill="none" stroke="#a6b4a7"/>'
    elif result:
        body = ('<g transform="translate(60 33) scale(1.65)">' + cat_tile(0, 0, "#e0af80")
                + '</g><text x="100" y="98" text-anchor="middle">1 image complete</text>')
    else:
        body = ('<rect x="40" y="41" width="120" height="34" rx="4" fill="#6f988c"/>'
                '<text x="100" y="62" text-anchor="middle" fill="#fffaf0">Generate</text>')
    return f"""
<g transform="translate(687 73)" font-family="sans-serif" font-size="15" fill="#354940">
  <rect width="204" height="134" rx="5" fill="#576b65"/>
  <rect x="5" y="6" width="194" height="121" rx="2" fill="#edf0e3"/>
  <text x="18" y="27" font-weight="bold">{header}</text>
  <path d="M18 34h164" stroke="#a6b4a7"/>
  {body}
</g>"""


def actions(t, last_line, frame_sample, rate):
    age = (frame_sample - last_line["start_sample"]) / rate
    progress = frame_sample / rate
    beat = last_line["beat"]
    action = last_line.get("action", "")
    speaker = last_line.get("speaker")
    hold = progress - last_line["start_sample"] / rate
    focus = min(1, max(0, age * 4), max(0, (1.65 - age) * 3))
    blink = t % 3.75 < 0.10
    walter_listening = (beat == "escalation" and speaker == "Kyle") or beat == "punchline"
    closing = beat == "outro" and action == "The fans spin up over the kitten result"
    reaction = min(1, max(0, (hold - 0.35) * 2)) if action == "Kyle perks up and Walter absorbs the reveal" else 0
    walter_pose = (
        -0.4 * focus if walter_listening else 0,
        0.65 * max(focus, reaction) if walter_listening else 0,
        0.65 * focus if speaker == "Walter" and beat == "outro" else 0,
        max(reaction, 0.55 if (walter_listening or closing) else 0),
        blink and speaker != "Walter",
    )
    if beat == "punchline":
        kyle_action = ("raise_brow", max(0.6, reaction)) if speaker != "Kyle" else ("present", focus)
    else:
        kyle_action = ("present", focus) if speaker == "Kyle" else ("blink", float(blink))
    sheet = 1 if beat == "punchline" else 0
    return walter_pose, kyle_action, sheet, closing


def frame(index, cue, beat, rate):
    t = index / FPS
    frame_sample = index * rate // FPS
    pose_time = (index // 2) / (FPS // 2)
    record = cue if frame_sample < cue["end_sample"] else {**cue, "speaker": None}
    mouth = {speaker: "X" for speaker in SPEAKERS}
    speaker = record.get("speaker")
    if speaker:
        local = (frame_sample - record["start_sample"]) / rate
        mouth[speaker] = next((shape["value"] for shape in record["mouth_cues"]
                               if shape["start"] <= local < shape["end"]), "X")
    pose_sample = (index // 2 * 2) * rate // FPS
    walter_pose, kyle_action, lift, closing = actions(pose_time, record, pose_sample, rate)
    reveal = beat == "punchline" and (speaker == "Susan" or "spreadsheet" not in cue.get("action", ""))
    if speaker == "Susan":
        reveal = frame_sample > cue["start_sample"] + rate // 2
        lift = min(1, 0.35 + (t - cue["start_sample"] / rate) * 3)
    parts = [
        OFFICE,
        monitor(beat, reveal, closing),
        tower(int(pose_time * 2) % 4),
        walter(mouth["Walter"], walter_pose, x=405 if beat == "outro" else 290),
    ]
    if beat != "outro":
        parts.append(kyle(mouth["Kyle"], *kyle_action, x=505 if beat == "punchline" else 537))
    if beat == "punchline":
        parts.append(susan(mouth["Susan"], lift, pose_time % 4.5 < 0.11 and speaker != "Susan", x=722))
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540">' + "".join(parts) + "</svg>"


def final_mix(samples, rate, timeline):
    closing = timeline[-1]["start_sample"]
    mixed = samples.copy()
    seconds = np.arange(len(samples) - closing) / rate
    ramp = np.minimum(1, seconds / 1.7)
    phase = 2 * np.pi * np.cumsum(36 + 48 * ramp) / rate
    fade = np.minimum(1, (len(seconds) - 1 - np.arange(len(seconds))) / (0.16 * rate))
    fan = 0.022 * ramp * fade * (np.sin(phase) + 0.25 * np.sin(3 * phase))
    mixed[closing:] += fan
    return mixed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path)
    parser.add_argument("timing", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--cues", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"Output already exists: {args.output}")
    data = json.loads(args.timing.read_text(encoding="utf-8"))
    samples, rate = sf.read(args.audio, dtype="float32")
    timeline = data["timeline"]
    if rate != data["sample_rate"] or samples.ndim != 1 or len(samples) != timeline[-1]["end_sample"]:
        raise ValueError("Timing and dialogue WAV must describe the same mono performance")
    audio_hash = hashlib.sha256(args.audio.read_bytes()).hexdigest()
    timing_hash = hashlib.sha256(args.timing.read_bytes()).hexdigest()
    existing = args.cues.exists()
    with TemporaryDirectory() as directory:
        temp = Path(directory)
        if existing:
            saved = json.loads(args.cues.read_text(encoding="utf-8"))
            if saved["audio_sha256"] != audio_hash or saved["timing_sha256"] != timing_hash:
                raise ValueError("The saved cues belong to a different performance")
            timeline = saved["timeline"]
        else:
            lip_sync(timeline, samples, rate, temp)

        mix = temp / "mix.wav"
        sf.write(mix, final_mix(samples, rate, timeline), rate, subtype="PCM_16")
        cache = {}
        cue_index = 0
        for index in range(math.ceil(len(samples) * FPS / rate)):
            sample = index * rate // FPS
            while cue_index + 1 < len(timeline) and sample >= timeline[cue_index + 1]["start_sample"]:
                cue_index += 1
            cue = timeline[cue_index]
            svg = frame(index, cue, cue["beat"], rate)
            png = temp / f"frame-{index:05}.png"
            if svg in cache:
                os.link(cache[svg], png)
            else:
                run("rsvg-convert", "-w", "1920", "-h", "1080", "-o", str(png), input=svg.encode())
                cache[svg] = png
        run("ffmpeg", "-loglevel", "error", "-n", "-framerate", str(FPS),
            "-i", str(temp / "frame-%05d.png"), "-i", str(mix), "-shortest",
            "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p", "-c:a", "aac",
            "-movflags", "+faststart", str(args.output))
        if not existing:
            with args.cues.open("x", encoding="utf-8") as out:
                out.write(json.dumps({"audio_sha256": audio_hash, "timing_sha256": timing_hash,
                                      "timeline": timeline}, ensure_ascii=False, indent=2) + "\n")
        print(f"{args.output}: {len(samples) / rate:.2f}s, {len(cache)} unique rendered frames")


if __name__ == "__main__":
    main()
