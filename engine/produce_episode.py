"""Start production for an episode with a ready renderer."""

import argparse
from pathlib import Path
import subprocess
import sys


ENGINE = Path(__file__).resolve().parent
RENDERERS = {
    "S01E01": "render_s01e01_final.py",
    "S01E02": "render_s01e02.py",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    plans = {path.name.removesuffix("-scenes.json"): path
             for path in (ENGINE.parent / "episodes").glob("S[0-9][0-9]E[0-9][0-9]-scenes.json")}
    parser.add_argument("episode", type=str.upper, choices=sorted(RENDERERS.keys() | plans.keys()))
    parser.add_argument("--output", type=Path, help="Write an alternate MP4 without replacing the episode export")
    args = parser.parse_args()

    if args.episode in RENDERERS:
        command = [sys.executable, str(ENGINE / RENDERERS[args.episode])]
    else:
        command = [sys.executable, str(ENGINE / "render_scene_plan.py"), str(plans[args.episode])]
    if args.output is not None:
        command.extend(("--output", str(args.output.resolve())))
    return subprocess.run(command, cwd=ENGINE.parent).returncode


if __name__ == "__main__":
    raise SystemExit(main())
