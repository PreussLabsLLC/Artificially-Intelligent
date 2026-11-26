"""Render Walter's pilot voice audition with Rhubarb and an SVG cutout."""

import argparse
import json
import math
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from walter_shot import LINE, validate_shot

FPS = 24
INK = "#25232a"
SKIN = "#f6c797"
MOUTHS = {
    "X": '<path d="M-9 2 Q0 -3 9 2" fill="none"/>',
    "A": '<path d="M-10 0 Q0 3 10 0" fill="none"/>',
    "B": '<rect x="-12" y="-4" width="24" height="8" rx="4" fill="#fff3df"/>',
    "C": '<ellipse rx="13" ry="7" fill="#46262d"/><path d="M-8 -4 H8" stroke="#fff3df"/>',
    "D": '<ellipse rx="13" ry="11" fill="#46262d"/><path d="M-6 5 Q0 0 6 5" stroke="#df8883"/>',
    "E": '<ellipse rx="9" ry="8" fill="#46262d"/>',
    "F": '<ellipse rx="6" ry="8" fill="#46262d"/>',
    "G": '<path d="M-10 -3 H10 Q9 8 0 7 Q-9 8 -10 -3Z" fill="#46262d"/><path d="M-7 -1 H7" stroke="#fff3df"/>',
    "H": '<ellipse rx="11" ry="8" fill="#46262d"/><path d="M-6 2 Q0 -3 6 2" stroke="#df8883"/>',
}

OFFICE = """
<path fill="#a9b3ad" d="M0 0H960V388H0z"/>
<path fill="#777d78" d="M0 388H960V540H0z"/>
<path fill="#8f9a92" d="M0 378H960V392H0z"/>
<g stroke="#74827c" stroke-width="5">
  <rect x="63" y="65" width="225" height="164" rx="4" fill="#cad9d5"/>
  <path d="M175 66V228M64 148H287"/>
</g>
<path fill="#b4c5c2" d="M69 211v-30h30v-24h27v24h26v-13h17v52H69zm111 9v-42h28v-13h25v22h16v-27h32v60z"/>
<rect x="685" y="73" width="205" height="136" rx="5" fill="#697873"/>
<rect x="691" y="79" width="193" height="122" rx="2" fill="#e0ded0"/>
<g fill="none" stroke="#82908a" stroke-width="3" stroke-linecap="round">
  <path d="M718 106h60m-60 12h44m-44 12h51m-51 12h33"/>
  <path d="M791 161h64m-58 0v-47m0 35 17-9 12 5 25-24"/>
</g>
<path fill="#674f42" d="M650 337h310v18H650zM681 355h18v185h-18z"/>
<path fill="#9c7a61" d="M670 316h290v21H650z"/>
<path fill="#555d5b" d="M785 311h74v6h-74zM813 270h17v43h-17z"/>
<rect x="757" y="228" width="124" height="66" rx="5" fill="#495351"/>
<rect x="764" y="235" width="110" height="52" rx="3" fill="#697c7d"/>
<path fill="none" stroke="#95aaaa" stroke-width="2" d="M776 249h44m-44 7h33m-33 7h49"/>
<path fill="#e5d9b7" d="M716 293h21v23h-21z"/>
<path fill="none" stroke="#e5d9b7" stroke-width="4" d="M736 297q14 0 9 9-2 4-9 4"/>
"""


def eye(x, gaze, openness):
    if openness == 0:
        return f'<path d="M{x - 19} 0q19 8 38 0" fill="none"/>'
    return f"""
      <g transform="translate({x} 0) scale(1 {openness})">
        <ellipse rx="20" ry="21" fill="#fff9eb"/>
        <circle cx="{gaze}" cy="1" r="4.8" fill="{INK}" stroke="none"/>
      </g>"""


def acting_pose(t, question, end, shot):
    # Hold acting poses for two output frames while sampling the mouth at 24 fps.
    pose_time = math.floor(t * 12) / 12
    reaction = min(1, max(0, (pose_time - question + 0.17) * 5))
    emphasis = max(0, 1 - abs(pose_time - question - 0.27) * 2.7)
    blinking = any(start <= pose_time < start + 0.10 for start in (question - 0.33, end + 0.43))
    if shot is None:
        return reaction, reaction, emphasis, reaction, blinking

    anchors = {
        "before_question": max(0, question - 0.25),
        "on_question": question,
        "after_line": end,
    }
    tilt = brow = gesture = stare = 0
    blinking = False
    for cue in shot["cues"]:
        elapsed = pose_time - anchors[cue["anchor"]]
        if elapsed < 0:
            continue
        action = cue["action"]
        transient = max(0, min(elapsed * 12 + 0.25, 1, (0.7 - elapsed) * 4))
        if action == "blink":
            blinking |= elapsed < 1 / 6
        elif action == "head_tilt":
            tilt = max(tilt, transient)
        elif action == "raise_brow":
            brow = max(brow, transient)
        elif action == "arm_gesture":
            gesture = max(gesture, transient)
        elif action == "hold_stare":
            stare = 1
    return tilt, brow, gesture, stare, blinking


def frame(t, mouth, question, end, shot=None):
    pose = acting_pose(t, question, end, shot)
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540">{OFFICE}{walter(mouth, pose)}</svg>'


def walter(mouth, pose, x=455):
    tilt, brow, gesture, stare, blinking = pose
    eyes = 0 if blinking else 1 - stare * 0.24
    gaze = 4 + stare * 5
    return f"""
<ellipse cx="{x}" cy="464" rx="102" ry="13" fill="#343941" opacity=".28"/>
<g transform="translate({x} 285) scale(1.4)" stroke="{INK}" stroke-width="3"
   stroke-linecap="round" stroke-linejoin="round">
  <g id="legs" fill="#45464b">
    <path d="M-44 86h88l-4 32H-40Z"/><path d="M0 99v18"/>
  </g>
  <g id="shoes" fill="#2f2e33">
    <path d="M-44 121q-3-13 38-10l6 10Zm44 0 5-10q40-3 39 10Z"/>
  </g>
  <g id="sweater" fill="#416a90">
    <path d="M-35 23Q-53 36-49 92Q0 103 49 92Q53 36 35 23Z"/>
    <path d="M-45 86Q0 95 45 86" fill="none" stroke="#345574"/>
  </g>
  <g id="arm-right" transform="rotate({-8 * gesture} -39 35)">
    <path d="M-38 31Q-61 33-68 75L-49 81Q-40 66-36 52" fill="#416a90"/>
    <path d="M-68 75q-5 24 11 23 10-1 8-17Z" fill="{SKIN}"/>
  </g>
  <g id="arm-left" transform="rotate({-21 * gesture} 39 35)">
    <path d="M38 31Q61 33 68 75L49 81Q40 66 36 52" fill="#416a90"/>
    <path d="M68 75q5 24-11 23-10-1-8-17Z" fill="{SKIN}"/>
  </g>
  <path id="collar" d="M-29 24l12 21L0 35l17 10 12-21Z" fill="#f3eee2"/>
  <g id="head" transform="rotate({-7 * tilt} 0 31) translate(0 {-3 * gesture})">
    <path d="M-57-25C-59-65-38-84 0-84S59-65 57-25C56 10 31 35 0 35S-56 10-57-25Z" fill="{SKIN}"/>
    <path id="hair" d="M-56-35q-6-17 1-31l-5 2q13-29 52-23 23-11 46 1 16 8 22 29l-6-6q7 14 3 30L26-65 8-54-14-68Z" fill="#929396"/>
    <g id="eyes" transform="translate(0 -19)" stroke-width="2.4">
      {eye(-19, gaze, eyes)}{eye(21, gaze, eyes)}
    </g>
    <g id="brows" fill="none" stroke-width="3.4">
      <path d="M-37 {-40 - 6 * brow} Q-23 {-49 - 6 * brow} -8 {-41 + 3 * brow}"/>
      <path d="M7 {-41 - 10 * brow} Q22 {-49 - 12 * brow} 37 {-40 - 10 * brow}"/>
    </g>
    <g id="mouth" transform="translate(2 15)" stroke-width="2.4">{MOUTHS[mouth]}</g>
  </g>
</g>"""


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wav", type=Path)
    parser.add_argument("mp4", type=Path)
    parser.add_argument("--shot", type=Path, help="Validated Walter shot JSON")
    args = parser.parse_args()
    shot = None
    if args.shot:
        shot = json.loads(args.shot.read_text(encoding="utf-8"))
        validate_shot(shot)
    with TemporaryDirectory() as directory:
        temp = Path(directory)
        transcript = temp / "dialog.txt"
        transcript.write_text(LINE, encoding="utf-8")
        cues_path = temp / "cues.json"
        run("rhubarb", "-q", "-f", "json", "-d", str(transcript),
            "-o", str(cues_path), str(args.wav))
        timing = json.loads(cues_path.read_text(encoding="utf-8"))
        cues = timing["mouthCues"]
        end = timing["metadata"]["duration"]
        # The first utterance ends before the longest interior rest in this take.
        pause = max((cue for cue in cues[1:-1] if cue["value"] == "X"),
                    key=lambda cue: cue["end"] - cue["start"], default=None)
        question = pause["end"] if pause else end * 0.65
        acting_end = cues[-1]["start"] if shot and cues[-1]["value"] == "X" else end
        for index in range(math.ceil((end + 1.25) * FPS)):
            t = index / FPS
            mouth = next((cue["value"] for cue in cues if cue["start"] <= t < cue["end"]), "X")
            run("rsvg-convert", "-w", "1920", "-h", "1080", "-o",
                str(temp / f"{index:04}.png"),
                input=frame(t, mouth, question, acting_end, shot).encode())
        run("ffmpeg", "-loglevel", "error", "-n", "-framerate", str(FPS), "-i",
            str(temp / "%04d.png"), "-i", str(args.wav), "-af", "apad", "-shortest",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags",
            "+faststart", str(args.mp4))


if __name__ == "__main__":
    main()
