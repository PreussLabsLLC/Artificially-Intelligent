"""Render the three-line Walter and Kyle pilot exchange in santa-dev."""

import argparse
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import Request, urlopen
from zipfile import ZipFile

import numpy as np
import soundfile as sf
from jsonschema import validate

from render_walter import FPS, INK, MOUTHS, OFFICE, SKIN, eye, run, walter
from walter_shot import LINE

LINES = (LINE, "Synthetic feline content, Walter.", "They're cats, Kyle.")
ACTIONS = {
    "walter": ["blink", "head_tilt", "raise_brow", "arm_gesture"],
    "kyle": ["blink", "nod", "raise_brow", "present"],
}
RATE = 24000


def acting_schema():
    properties = {
        key: {"enum": ACTIONS[character]}
        for key, character in (
            ("line_1_walter", "walter"), ("line_1_kyle", "kyle"),
            ("line_2_walter", "walter"), ("line_2_kyle", "kyle"),
            ("line_3_walter", "walter"), ("line_3_kyle", "kyle"),
        )
    }
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


def direct(url):
    schema = acting_schema()
    request = Request(
        url.rstrip("/") + "/v1/chat/completions",
        headers={"Content-Type": "application/json"},
        data=json.dumps({
            "messages": [{"role": "user", "content": (
                "Direct an office cutout comedy in six acting cues, one for each character "
                "on each line. The cue lands halfway into its line's speech, so a listener "
                "can visibly react to the speaker. Walter is dry and increasingly skeptical. "
                "Kyle is an upbeat founder who thinks his euphemism explains everything. "
                "Give Walter a readable skeptical reaction during Kyle's middle line. "
                'The exchange is 1 Walter: "' + LINES[0] + '" 2 Kyle: "' + LINES[1] +
                '" 3 Walter: "' + LINES[2] + '". A final silent Walter stare is added '
                "afterward. Choose one action per field. " + json.dumps(schema)
            )}],
            "max_tokens": 768,
            "temperature": 0,
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "pilot_acting", "strict": True, "schema": schema,
            }},
        }).encode(),
    )
    with urlopen(request, timeout=120) as response:
        completion = json.load(response)
    plan = json.loads(completion["choices"][0]["message"]["content"])
    validate(plan, schema)
    return plan


def kyle(mouth, action, amount, x=600):
    nod = 6 * amount if action == "nod" else 0
    brow = 8 * amount if action == "raise_brow" else 0
    arm = 48 * amount if action == "present" else 0
    openness = 0 if action == "blink" and amount > 0.5 else 1
    smile = '<path d="M-11 -2Q0 5 11 -4" fill="none"/>'
    return f"""
<ellipse cx="{x}" cy="464" rx="102" ry="13" fill="#343941" opacity=".28"/>
<g transform="translate({x} 285) scale(1.4)" stroke="{INK}" stroke-width="3"
   stroke-linecap="round" stroke-linejoin="round">
  <path d="M-44 85h88l-4 33H-40Z" fill="#44484a"/>
  <path d="M0 100v16" fill="none"/>
  <path d="M-44 121q-3-13 38-10l6 10Zm44 0 5-10q40-3 39 10Z" fill="#2f3033"/>
  <path d="M-35 25Q-53 36-49 92Q0 103 49 92Q53 36 35 25Z" fill="#43883e"/>
  <path d="M-23 78q6-4 10-12h26q4 8 10 12v8h-46Z" fill="#397636" stroke="#326c31"/>
  <g transform="rotate({arm} -39 35)">
    <path d="M-38 31Q-61 33-68 75L-49 81Q-40 66-36 52" fill="#43883e"/>
    <path d="M-68 75q-5 24 11 23 10-1 8-17Z" fill="{SKIN}"/>
  </g>
  <path d="M38 31Q61 33 68 75L49 81Q40 66 36 52" fill="#43883e"/>
  <path d="M68 75q5 24-11 23-10-1-8-17Z" fill="{SKIN}"/>
  <path d="M-38 25q11-22 38-21 29 0 38 21L15 44 0 36-15 44Z" fill="#58a04e"/>
  <path d="M-12 38l-3 22m27-22 3 22" stroke="#f3ebd4"/>
  <g transform="rotate({nod} 0 30)">
    <path d="M-56-29C-56-57-31-71 0-71S56-57 56-29C55 7 29 34 0 34S-55 7-56-29Z" fill="{SKIN}"/>
    <path d="M-55-26l-7-15 9 2-11-17 18-2-8-13 22 1-8-17 28 9L3-99l9 19 27-9-7 16 23 5-9 8 16 15-10 2 3 16-25-32-11 11-10-14-15 14-12-11-12 13-7-4Z" fill="#805433"/>
    <g transform="translate(0 -16)" stroke-width="2.4">{eye(-19, -5, openness)}{eye(21, -5, openness)}</g>
    <path d="M-36 {-40-brow}q14-9 28-1M7 {-41-brow}q15-9 29 1" fill="none"/>
    <g transform="translate(-4 16)" stroke-width="2.4">{smile if mouth == "X" else MOUTHS[mouth]}</g>
  </g>
</g>"""


def dialogue(opening, temp):
    from kokoro import KPipeline

    approved, rate = sf.read(opening, dtype="float32")
    if approved.ndim != 1 or rate != RATE:
        raise ValueError("Expected the approved 24 kHz mono Walter recording")
    pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M", device="cpu")
    takes = [approved]
    for line, voice, speed in zip(LINES[1:], ("am_fenrir", "am_michael"), (1.07, 0.93)):
        takes.append(np.concatenate([
            result.audio.numpy() for result in pipeline(line, voice=voice, speed=speed)
        ]))

    timeline = []
    start = 0
    for index, (line, take) in enumerate(zip(LINES, takes)):
        wav = temp / f"line-{index}.wav"
        transcript = temp / f"line-{index}.txt"
        cue_file = temp / f"line-{index}.json"
        sf.write(wav, take, RATE, subtype="PCM_16")
        transcript.write_text(line, encoding="utf-8")
        run("rhubarb", "-q", "-f", "json", "-d", str(transcript), "-o", str(cue_file), str(wav))
        cues = json.loads(cue_file.read_text(encoding="utf-8"))["mouthCues"]
        voiced = [cue for cue in cues if cue["value"] != "X"]
        if not voiced:
            raise ValueError(f"Rhubarb found no speech on line {index + 1}")
        timeline.append((start / RATE, cues, voiced[0]["start"], voiced[-1]["end"]))
        start += len(take)

    end = timeline[-1][0] + timeline[-1][3]
    sample_count = max(start, math.ceil((end + 1.65) * RATE))
    audio = np.pad(np.concatenate(takes), (0, sample_count - start))
    t = np.arange(len(audio)) / RATE
    ramp = np.clip((t - end) / 1.25, 0, 1)
    phase = 2 * np.pi * np.cumsum(37 + 47 * ramp) / RATE
    fan = 0.031 * ramp * (np.sin(phase) + 0.28 * np.sin(3 * phase))
    sf.write(temp / "mix.wav", np.clip(audio + fan, -1, 1), RATE, subtype="PCM_16")
    return timeline, end, len(audio) / RATE


def acting(t, timeline, plan):
    mouths = {"walter": "X", "kyle": "X"}
    poses = {"walter": ("blink", 0), "kyle": ("blink", 0)}
    pose_time = math.floor(t * 12) / 12
    for index, (start, cues, first, last) in enumerate(timeline, 1):
        speaker = "kyle" if index == 2 else "walter"
        local = t - start
        if 0 <= local < cues[-1]["end"]:
            mouths[speaker] = next((c["value"] for c in cues if c["start"] <= local < c["end"]), "X")
        if index == 1:
            # React to the second clause so the original comic pause has room.
            gap = max((c for c in cues[1:-1] if c["value"] == "X"),
                      key=lambda c: c["end"] - c["start"], default=None)
            beat = gap["end"] if gap else (first + last) / 2
        else:
            beat = first + (last - first) * 0.56
        age = pose_time - start - beat
        if 0 <= age < 0.67:
            for character in poses:
                action = plan[f"line_{index}_{character}"]
                weight = float(age < 1 / 6) if action == "blink" else min(age * 12 + 0.3, 1, (0.67 - age) * 4)
                poses[character] = (action, weight)
    return mouths, poses


def record_performance(path, mix, plan, timeline, end):
    metadata = {"version": 1, "lines": LINES, "acting": plan, "timeline": timeline, "end": end}
    with TemporaryDirectory(dir=path.parent) as directory:
        staged = Path(directory) / path.name
        with ZipFile(staged, "w") as archive:
            archive.write(mix, "mix.wav")
            archive.writestr("performance.json", json.dumps(metadata))
        staged.replace(path)


def replay_performance(path, mix):
    with ZipFile(path) as archive:
        saved = json.loads(archive.read("performance.json"))
        if saved["version"] != 1 or tuple(saved["lines"]) != LINES:
            raise ValueError("The recording belongs to a different pilot or format version")
        validate(saved["acting"], acting_schema())
        mix.write_bytes(archive.read("mix.wav"))
    audio = sf.info(mix)
    if audio.samplerate != RATE or audio.channels != 1:
        raise ValueError("Expected a 24 kHz mono pilot mix")
    return saved["acting"], saved["timeline"], saved["end"], audio.frames / RATE


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("opening", nargs="?", type=Path, help="Approved opening WAV for a new take")
    parser.add_argument("output", type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--url", default="http://walter-llm:8080")
    performance = parser.add_mutually_exclusive_group()
    performance.add_argument("--record", type=Path, help="Save the mix and timing in a ZIP")
    performance.add_argument("--replay", type=Path, help="Render with a previously recorded ZIP")
    args = parser.parse_args()
    if args.opening is None and not args.replay:
        parser.error("An opening WAV is required when recording a new take")
    if args.output.exists():
        parser.error(f"Output already exists: {args.output}")
    if args.record and args.record.exists():
        parser.error(f"Performance already exists: {args.record}")
    with TemporaryDirectory() as directory:
        temp = Path(directory)
        mix = temp / "mix.wav"
        if args.replay:
            plan, timeline, end, duration = replay_performance(args.replay, mix)
        else:
            plan = direct(args.url)
            timeline, end, duration = dialogue(args.opening, temp)
        print(json.dumps(plan, indent=2), flush=True)
        for index in range(math.ceil(duration * FPS)):
            t = index / FPS
            mouths, poses = acting(t, timeline, plan)
            action, amount = poses["walter"]
            closing = t >= end
            pose = (
                amount if action == "head_tilt" and not closing else 0,
                amount if action == "raise_brow" and not closing else 0,
                amount if action == "arm_gesture" and not closing else 0,
                float(closing),
                action == "blink" and amount > 0.5 and not closing,
            )
            scene = (
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540">'
                + OFFICE + walter(mouths["walter"], pose, x=340)
                + kyle(mouths["kyle"], *poses["kyle"]) + '</svg>'
            )
            run("rsvg-convert", "-w", "1920", "-h", "1080", "-o",
                str(temp / f"{index:04}.png"), input=scene.encode())
        run("ffmpeg", "-loglevel", "error", "-n", "-framerate", str(FPS), "-i",
            str(temp / "%04d.png"), "-i", str(mix), "-shortest",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags",
            "+faststart", str(args.output))
        info = [{"line": line, "speech_start": round(start + first, 2),
                 "speech_end": round(start + last, 2)}
                for line, (start, _, first, last) in zip(LINES, timeline)]
        args.plan.write_text(json.dumps({"acting": plan, "timing": info}, indent=2) + "\n",
                             encoding="utf-8")
        if args.record:
            record_performance(args.record, mix, plan, timeline, end)
        print(json.dumps(info), flush=True)


if __name__ == "__main__":
    main()
