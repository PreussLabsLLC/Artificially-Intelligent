"""Check recorded dialogue against the screenplay with local Whisper."""

import argparse
import json
from pathlib import Path
import re
import subprocess
import unicodedata


def words(text):
    text = unicodedata.normalize("NFKC", text).casefold()
    return re.findall(r"[^\W_]+", text.replace("’", "").replace("'", ""))


def main():
    from faster_whisper import WhisperModel
    import numpy as np

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path)
    parser.add_argument("timing", type=Path)
    parser.add_argument("--verbose", action="store_true", help="Print every transcript")
    args = parser.parse_args()
    timing = json.loads(args.timing.read_text(encoding="utf-8"))
    rate = timing["sample_rate"]
    audio = np.frombuffer(subprocess.check_output([
        "ffmpeg", "-v", "error", "-i", str(args.audio), "-map", "0:a:0",
        "-ar", "16000", "-ac", "1", "-f", "f32le", "-",
    ]), dtype="<f4")
    model = WhisperModel("small.en", device="cpu", compute_type="int8", cpu_threads=4)

    checked = flagged = 0
    for cue in timing["timeline"]:
        if "speaker" not in cue:
            continue
        start, end = cue["start_sample"], cue["end_sample"]
        take = audio[round(start * 16000 / rate):round(end * 16000 / rate)]
        segments, _ = model.transcribe(take, language="en", condition_on_previous_text=False)
        transcript = " ".join(segment.text.strip() for segment in segments).strip()
        expected, heard = words(cue["line"]), words(transcript)
        checked += 1
        needs_review = not heard or expected != heard
        if needs_review:
            flagged += 1
        if needs_review or args.verbose:
            print(f"{start / rate:6.2f}s {cue['speaker']}: "
                  f"expected {cue['line']!r}, heard {transcript!r}", flush=True)
    print(f"Dialogue check: {flagged} of {checked} lines flagged for listening.", flush=True)


if __name__ == "__main__":
    main()
