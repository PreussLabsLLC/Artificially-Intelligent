"""Render Susan's spreadsheet reveal from the approved Marlo recording."""

import argparse
import hashlib
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory

import soundfile as sf

from render_pilot import kyle
from render_walter import FPS, INK, MOUTHS, OFFICE, SKIN, eye, run, walter

LINE = "The cat account is our only source of revenue."
LEAD = 0.75
TAIL = 1.55


def susan(mouth, lift, blink, x=690):
    arm = -45 * lift
    return f"""
<ellipse cx="{x}" cy="464" rx="99" ry="13" fill="#343941" opacity=".28"/>
<g transform="translate({x} 285) scale(1.4)" stroke="{INK}" stroke-width="3"
   stroke-linecap="round" stroke-linejoin="round">
  <path id="susan-hair-back" d="M-57-60Q-43-91-8-91Q29-92 48-66Q58-50 61-19
    Q64 4 76 14Q65 29 41 28H-43Q-66 29-75 17Q-63 8-62-19Q-63-42-57-60Z" fill="#45332e"/>
  <path d="M-43 86h86l-4 32H-39Z" fill="#424047"/>
  <path d="M0 99v18" fill="none"/>
  <path d="M-43 121q-4-13 36-10l7 10Zm43 0 5-10q39-3 38 10Z" fill="#2f2d33"/>
  <path d="M-33 22Q-56 39-49 92Q0 103 49 92Q56 39 33 22Z" fill="#765492"/>
  <path d="M-38 30Q-60 33-65 79l16 4q9-13 12-31" fill="#765492"/>
  <path d="M-65 79q-2 20 10 18 9-2 6-14Z" fill="{SKIN}"/>
  <path d="M-31 23l12 23L0 35l19 11 12-23Z" fill="#f8f3ed"/>
  <g id="susan-sheet-arm" transform="rotate({arm} 39 34)">
    <path d="M38 30Q59 33 64 77l-17 6q-9-13-12-31" fill="#765492"/>
    <g transform="translate(58 79) rotate({-arm - 13})">
      <path d="M-8-12v-35h30l9 9v33H-8Z" fill="#f6f0da"/>
      <path d="M22-47v9h9M-2-32h25M-2-25h25M-2-18h25M7-32v14"
        fill="none" stroke="#8e9984" stroke-width="1.5"/>
      <path d="M-8-3q-3-10 4-12 6-2 8 4l6 1Q12 1 2 3-3 4-8-3Z" fill="{SKIN}"/>
    </g>
  </g>
  <path d="M-53-23C-57-57-36-80 0-80S56-56 53-23C50 12 28 35 0 35S-50 12-53-23Z"
    fill="{SKIN}"/>
  <path id="susan-hair-fringe" d="M-59-21q-4-54 36-66 48-13 72 23 13 16 9 45l-7 9
    Q40-35 20-46 8-54 2-67-14-48-47-39l-5 26Z" fill="#45332e"/>
  <g transform="translate(0 -15)" stroke-width="2.3">
    {eye(-18, -5, 0 if blink else 0.84)}{eye(20, -5, 0 if blink else 0.84)}
  </g>
  <path d="M-34-36q13-6 25-1m15 0q13-5 25 2" fill="none" stroke-width="2.8"/>
  <circle cx="-49" cy="0" r="3" fill="#f4eee4" stroke="none"/>
  <circle cx="48" cy="0" r="3" fill="#f4eee4" stroke="none"/>
  <g transform="translate(-1 14)" stroke-width="2.4">{MOUTHS[mouth]}</g>
</g>"""


def make_shot(audio, source_hash, duration, temp):
    transcript = temp / "reveal.txt"
    transcript.write_text(LINE, encoding="utf-8")
    output = temp / "rhubarb.json"
    run("rhubarb", "-q", "-f", "json", "-d", str(transcript),
        "-o", str(output), str(audio))
    cues = json.loads(output.read_text(encoding="utf-8"))["mouthCues"]
    speech = [cue for cue in cues if cue["value"] != "X"]
    start, end = speech[0]["start"], speech[-1]["end"]
    return {
        "dialogue": LINE,
        "voice": "Piper Marlo",
        "audio_sha256": source_hash,
        "audio_offset": LEAD,
        "duration": round(LEAD + duration + TAIL, 6),
        "mouth_cues": cues,
        "actions": {
            "susan_sheet": LEAD + max(0, start - 0.16),
            "spreadsheet_reveal": LEAD + start + (end - start) * 0.50,
            "kyle_perks_up": LEAD + start + (end - start) * 0.65,
            "walter_reacts": LEAD + end + 0.30,
        },
    }


def frame(t, shot):
    pose_time = math.floor(t * 12 + 1e-8) / 12
    actions = shot["actions"]
    local = t - shot["audio_offset"]
    mouth = next((cue["value"] for cue in shot["mouth_cues"]
                  if cue["start"] <= local < cue["end"]), "X")
    lift = min(1, max(0, (pose_time - actions["susan_sheet"]) * 4))
    kyle_reaction = min(1, max(0, (pose_time - actions["kyle_perks_up"]) * 6))
    walter_reaction = min(1, max(0, (pose_time - actions["walter_reacts"]) * 4))
    board = ""
    if pose_time >= actions["spreadsheet_reveal"]:
        board = """
<rect x="692" y="79" width="191" height="122" rx="2" fill="#e5eadb"/>
<path d="M707 111h160M707 141h160" stroke="#95a58e" stroke-width="2"/>
<g font-family="sans-serif" fill="#394939">
  <text x="708" y="102" font-size="14" font-weight="bold">Revenue</text>
  <text x="708" y="131" font-size="15">Cat account</text>
  <text x="865" y="131" font-size="18" font-weight="bold" text-anchor="end">100%</text>
</g>"""
    walter_pose = (walter_reaction * -0.55, walter_reaction * 0.65, 0,
                   walter_reaction, 0.20 <= pose_time < 0.32)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540">'
        + OFFICE + board + walter("X", walter_pose, x=245)
        + kyle("X", "raise_brow", kyle_reaction, x=468)
        + susan(mouth, lift, 0.40 <= pose_time < 0.52) + "</svg>"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path, help="Approved Susan reveal WAV")
    parser.add_argument("video", type=Path)
    parser.add_argument("--shot", required=True, type=Path, help="Save or reuse the shot JSON")
    args = parser.parse_args()
    if args.video.exists():
        parser.error(f"Output already exists: {args.video}")
    source_hash = hashlib.sha256(args.audio.read_bytes()).hexdigest()
    duration = sf.info(args.audio).duration
    existing = args.shot.exists()
    with TemporaryDirectory() as directory:
        temp = Path(directory)
        shot = (json.loads(args.shot.read_text(encoding="utf-8")) if existing
                else make_shot(args.audio, source_hash, duration, temp))
        if shot["audio_sha256"] != source_hash or shot["dialogue"] != LINE:
            raise ValueError("The saved shot does not match the reveal recording")
        for index in range(math.ceil(shot["duration"] * FPS)):
            run("rsvg-convert", "-w", "1920", "-h", "1080",
                "-o", str(temp / f"{index:04}.png"), input=frame(index / FPS, shot).encode())
        delay_ms = round(shot["audio_offset"] * 1000)
        run("ffmpeg", "-loglevel", "error", "-n", "-framerate", str(FPS), "-i",
            str(temp / "%04d.png"), "-i", str(args.audio),
            "-af", f"adelay={delay_ms},apad", "-shortest", "-c:v", "libx264",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", str(args.video))
        if not existing:
            with args.shot.open("x", encoding="utf-8") as output:
                output.write(json.dumps(shot, indent=2) + "\n")


if __name__ == "__main__":
    main()
