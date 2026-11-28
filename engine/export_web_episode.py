"""Package a scene-plan episode as SVG, a timed layer track, and mixed audio."""

import argparse
import hashlib
from itertools import chain
import json
import math
from pathlib import Path
import re
from shutil import copyfile
from tempfile import TemporaryDirectory

import numpy as np
import soundfile as sf

import render_animatic as animatic
import render_s01e02 as episode_two
from episode_media import write_subtitles
from render_chip_audition import CHIP_LINE, KYLE_LINE, audition_layers, record_audition
from render_s01e01_final import CUES, SUBTITLES, TIMING
from render_scene_plan import (
    FPS, MUSIC, PIPER_MODEL, ROOT, SETS, actors, checked_input, frame_states, mix,
    monitor, prepare_audio, read_plan, title_layer,
)


def subtitle_seconds(stamp):
    hours, minutes, seconds = stamp.replace(",", ".").split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def subtitle_tracks(episode_id, timing, temp):
    if episode_id == "S01E01":
        sources = [(ROOT / "episodes/subtitles" / f"{episode_id}.{code}.srt", language, label)
                   for code, language, label in SUBTITLES]
    else:
        sources = write_subtitles(episode_id, timing["timeline"], temp)
    tracks = []
    for path, _, label in sources:
        cues = []
        for block in re.split(r"\n[ \t]*\n", path.read_text(encoding="utf-8-sig").strip()):
            _, span, line = block.split("\n", 2)
            start, end = map(subtitle_seconds, span.split(" --> "))
            cues.append([start, end, line])
        tracks.append({"code": path.stem.rsplit(".", 1)[1], "label": label, "cues": cues})
    return tracks


def write_browser_data(data, destination, variable):
    payload = json.dumps(data, separators=(",", ":"))
    destination.write_text(f"globalThis.{variable} = {payload};\n", encoding="utf-8")


def copy_season_index(folder):
    (folder / "bible").mkdir(exist_ok=True)
    season_file = "S01-Artificially-Intelligent.json"
    copyfile(ROOT / "bible" / season_file, folder / "bible" / season_file)
    season = json.loads((folder / "bible" / season_file).read_bytes())
    season["rendered"] = [episode["id"] for episode in season["episodes"]
                          if (folder / episode["id"] / "episode-data.js").is_file()]
    write_browser_data(season, folder / "season-data.js", "seasonData")
    copyfile(ROOT / "web" / "studio.css", folder / "studio.css")
    copyfile(ROOT / "web" / "season.html", folder / "index.html")
    (folder / ".nojekyll").touch()


def scene_layers(plan, timing, frame_count):
    fragments = {}
    for state in frame_states(timing["timeline"], frame_count):
        scene_index, speaker, mouth, card, acting, blink, title = state
        if state not in fragments:
            scene = plan["scenes"][scene_index]
            acting = dict(acting)
            layers = [SETS[scene["set"]], monitor(plan["cards"][card])]
            for name, x in scene["cast"].items():
                layers.append(actors({name: x}, speaker, mouth, acting, blink))
            if title:
                layers.append(title_layer(plan["title"]))
            fragments[state] = layers
        yield fragments[state]


def compile_layers(title, frame_count, frames):
    fragments = []
    layer_ids = {}

    def layer_id(svg):
        if svg not in layer_ids:
            layer_ids[svg] = len(fragments)
            fragments.append(svg)
        return layer_ids[svg]

    changes = []
    previous = None
    for frame, parts in enumerate(frames):
        layers = [layer_id(svg) for svg in parts]
        if layers != previous:
            changes.append([frame, layers])
            previous = layers

    return {
        "version": 1, "title": title, "fps": FPS, "frames": frame_count,
        "layers": fragments, "changes": changes,
    }


def saved_animatic(temp):
    timing_source = TIMING.read_bytes()
    timing = json.loads(timing_source)
    saved = json.loads(CUES.read_bytes())
    if hashlib.sha256(timing_source).hexdigest() != saved["timing_sha256"]:
        raise ValueError("The saved mouth cues belong to a different animatic timeline.")
    source = checked_input(ROOT / timing["audio_file"], saved["audio_sha256"])
    samples, rate = sf.read(source, dtype="float32")
    timeline = saved["timeline"]
    if rate != timing["sample_rate"] or samples.ndim != 1 or len(samples) != timeline[-1]["end_sample"]:
        raise ValueError("The saved timing and dialogue WAV must describe the same mono performance.")
    wav = temp / "dialogue.wav"
    sf.write(wav, animatic.final_mix(samples, rate, timeline), rate, subtype="PCM_16")
    count = math.ceil(len(samples) * FPS / rate)
    frames = (animatic.frame_layers(index, timeline[cue], timeline[cue]["beat"], rate)
              for index, cue in animatic.frame_cues(timeline, count, rate))
    draft = json.loads((ROOT / "episodes/S01E01-draft.json").read_bytes())
    return draft["title"], wav, timing, count, frames, 6.45


def chip_episode(pipeline, model, temp):
    draft = json.loads(episode_two.DRAFT.read_bytes())
    outro = draft["scenes"][-1]["dialogue"]
    if [turn["line"] for turn in outro] != [KYLE_LINE, CHIP_LINE]:
        raise ValueError("The outro dialogue must match the Chip audition.")
    rate = episode_two.RATE
    audition_temp = temp / "audition"
    audition_temp.mkdir()
    closing, cues = record_audition(pipeline, audition_temp)
    frame_samples = rate // FPS
    audio, timeline = episode_two.record(draft, pipeline, model, temp,
                                         draft["minimum_seconds"] - len(closing) / rate)
    animatic.lip_sync(timeline, audio, rate, temp)
    count = math.ceil(len(audio) / frame_samples)
    outro_start = count * frame_samples
    audio = np.concatenate((np.pad(audio, (0, outro_start - len(audio))), closing))
    last_line = (outro_start + cues[-1]["end_sample"]) / rate
    performance = list(timeline)
    for cue, turn in zip(cues, outro):
        performance.append({**cue, "de": turn["de"], "es": turn["es"],
                            "start_sample": outro_start + cue["start_sample"],
                            "end_sample": outro_start + cue["end_sample"]})
    performance.append({"start_seconds": last_line})
    duration = len(audio) / rate
    timing = {"duration_seconds": duration, "sample_rate": rate, "timeline": performance}
    wav = temp / "dialogue.wav"
    sf.write(wav, audio, rate, subtype="PCM_16")
    outro_frames = len(closing) // frame_samples
    frames = chain(episode_two.frame_layers(timeline, count, draft["title"]),
                   audition_layers(cues, outro_frames))
    return (draft["title"], wav, timing, count + outro_frames, (parts for _, parts in frames),
            round(last_line - duration + 10, 3))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("episode", help="Episode ID or path to a scene plan")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--piper-model", type=Path, default=Path("/cache/huggingface/hub") / PIPER_MODEL)
    parser.add_argument("--check-dialogue", action=argparse.BooleanOptionalAction, default=True,
                        help="Check dialogue for scene-plan episodes (default: enabled)")
    args = parser.parse_args()

    episode_id = args.episode.upper()
    try:
        plan = None
        if episode_id not in {"S01E01", "S01E02"}:
            source = Path(args.episode)
            if not source.suffix:
                source = ROOT / "episodes" / f"{episode_id}-scenes.json"
            plan = read_plan(source)
            episode_id = plan["episode"]
        tracks = {role: checked_input(ROOT / "assets/music" / name, digest)
                  for role, (name, digest) in MUSIC.items()}
    except (KeyError, ValueError, OSError) as error:
        parser.error(str(error))
    output = (args.output or ROOT / "web-build" / episode_id).resolve()
    if output.exists():
        parser.error(f"Output already exists: {output}")
    needs_piper = episode_id == "S01E02" or (plan and any("Susan" in scene["cast"] for scene in plan["scenes"]))
    if needs_piper and not args.piper_model.is_file():
        parser.error("Susan’s Piper model must be available locally.")

    if episode_id != "S01E01" or plan:
        from kokoro import KPipeline

        pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M", device="cpu")

    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as folder:
        temp = Path(folder)
        package = temp / "site"
        package.mkdir()
        if plan:
            wav, timing, frame_count = prepare_audio(plan, pipeline, args.piper_model, temp, args.check_dialogue)
            title = plan["title"]
            frames = scene_layers(plan, timing, frame_count)
            last_line = next(cue["end_sample"] / timing["sample_rate"]
                             for cue in reversed(timing["timeline"]) if "speaker" in cue)
            outro_rise = round(last_line - timing["duration_seconds"] + 10, 3)
        elif episode_id == "S01E01":
            title, wav, timing, frame_count, frames, outro_rise = saved_animatic(temp)
        else:
            title, wav, timing, frame_count, frames, outro_rise = chip_episode(pipeline, args.piper_model, temp)
        mix(wav, tracks, timing, [], package / "episode.m4a", temp,
            outro_rise=outro_rise, audio_only=True)
        episode = compile_layers(title, frame_count, frames)
        episode["subtitles"] = subtitle_tracks(episode_id, timing, temp)
        (package / "episode.json").write_text(json.dumps(episode, separators=(",", ":")), encoding="utf-8")
        write_browser_data(episode, package / "episode-data.js", "episodeData")
        (package / ".nojekyll").touch()
        for name in ("index.html", "player.js", "studio.css"):
            copyfile(ROOT / "web" / name, package / name)
        package.rename(output)
    if output.parent == (ROOT / "web-build").resolve():
        copy_season_index(output.parent)
    print(f"{output}: {timing['duration_seconds']:.3f}s, {len(episode['changes'])} SVG layer changes")


if __name__ == "__main__":
    main()
