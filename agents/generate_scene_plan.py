"""Generate a renderable office scene plan from a season outline."""

import argparse
import json
from pathlib import Path
import sys
import textwrap
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from jsonschema import ValidationError, validate

from writer import ROOT, closed_object

sys.path.insert(0, str(ROOT / "engine"))
from scene_plan import ACTIONS, OFFICE, validate_plan


LAYOUTS = {1: (440,), 2: (337, 590), 3: (245, 515, 763), 4: (166, 369, 563, 790)}


def text_field(limit):
    return {"type": "string", "minLength": 1, "maxLength": limit}


CARD = closed_object({"heading": text_field(22), "body": text_field(22), "label": text_field(25)})
ACTOR = {"enum": list(ACTIONS)}
ACTING = closed_object({
    name: {"enum": ["idle", *sorted(actions)]} for name, actions in ACTIONS.items()
})
TURN = closed_object({
    "speaker": ACTOR, "line": text_field(190), "de": text_field(220), "es": text_field(220),
    "acting": ACTING, "reveal": {"anyOf": [CARD, {"type": "null"}]},
})
SCENE = closed_object({
    "card": CARD,
    "lead_seconds": {"type": "integer", "minimum": 1, "maximum": 3},
    "tail_seconds": {"type": "integer", "minimum": 1, "maximum": 3},
    "dialogue": {"type": "array", "items": TURN, "minItems": 1},
})


def request_scenes(url, episode, cast, feedback):
    beats = {}
    minimum_turns = {}
    for beat in episode["outline"]:
        seconds = beat["end_seconds"] - beat["start_seconds"]
        name = beat["beat"]
        minimum_turns[name] = max(1, (seconds + 5) // 6)
        dialogue = {**SCENE["properties"]["dialogue"], "minItems": minimum_turns[name]}
        beats[name] = closed_object({**SCENE["properties"], "dialogue": dialogue})
    schema = closed_object(beats)
    prompt = (
        "Stage this episode of an animated workplace comedy in the standing office set. "
        "Write each outline beat as one scene. Keep the revelations in outline order through "
        "dialogue and short office monitor cards. Use only the four recurring characters. "
        "Represent offscreen people or actions through those characters and the monitor. "
        "Write dry, character-specific exchanges totaling roughly 110 to 145 spoken English "
        f"words, with at least this many distinct turns per beat: {json.dumps(minimum_turns)}. "
        "Use those turns for reactions and jokes grounded in the outline. "
        "Supply faithful standard German and neutral Latin American Spanish "
        "translations. The monitor's heading, body and label must each fit on one short line. "
        "Start each scene with a monitor card that establishes the situation while preserving "
        "any surprise. Within the scene, use a reveal card on the corresponding dialogue turn, "
        "or null to retain the current card. Give speakers and listeners occasional physical "
        "reactions. Only give a character a non-idle action if present in the scene. "
        "The cast is inferred from speakers and characters with non-idle actions. "
        "Never repeat an earlier turn verbatim.\n\n"
        f"CAST\n{cast}\n\nOUTLINE\n{json.dumps(episode, ensure_ascii=False)}"
        f"\n\nReturn an object keyed by beat name. Each beat uses this schema:\n{json.dumps(SCENE)}"
    )
    if feedback:
        prompt += f"\n\nCorrect this problem from the previous attempt: {feedback}"
    request = Request(
        url.rstrip("/") + "/v1/chat/completions",
        headers={"Content-Type": "application/json"},
        data=json.dumps({
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 6000,
            "reasoning_effort": "low",
            "temperature": 0.35,
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "office_scenes", "strict": True, "schema": schema,
            }},
        }).encode("utf-8"),
    )
    with urlopen(request, timeout=180) as response:
        payload = json.load(response)
    try:
        choice = payload["choices"][0]
        content = choice["message"]["content"]
    except (IndexError, KeyError, TypeError) as error:
        raise ValueError("The model returned no completion.") from error
    if choice.get("finish_reason") == "length":
        raise ValueError("The model hit its token limit. Keep the dialogue and staging concise.")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("The model returned an empty scene plan.")
    scenes = json.loads(content)
    validate(scenes, schema)
    return scenes


def card_lines(card):
    lines = [" ".join(card[field].split()) for field in ("heading", "body", "label")]
    if not all(lines):
        raise ValueError("Every monitor card needs three lines of text.")
    return lines


def assemble(episode, draft):
    cards = {}
    scenes = []
    spoken = set()
    for beat in episode["outline"]:
        name = beat["beat"]
        scene = draft[name]
        cards[name] = card_lines(scene["card"])
        cast = {}
        dialogue = []
        for index, turn in enumerate(scene["dialogue"], 1):
            speaker = turn["speaker"]
            cast.setdefault(speaker)
            acting = {actor: action for actor, action in turn["acting"].items() if action != "idle"}
            cast.update(acting)
            line = " ".join(turn["line"].split())
            if line.casefold() in spoken:
                raise ValueError(f"Repeated dialogue: {line}")
            spoken.add(line.casefold())
            cue = {"speaker": speaker, "line": line, "acting": acting}
            for language in ("de", "es"):
                cue[language] = textwrap.fill(" ".join(turn[language].split()), width=40,
                                              break_long_words=False, break_on_hyphens=False)
            if turn["reveal"]:
                key = f"{name}-{index}"
                cards[key] = card_lines(turn["reveal"])
                cue["screen"] = {"card": key, "after": 0}
            dialogue.append(cue)
        scenes.append({
            "set": OFFICE, "cast": dict(zip(cast, LAYOUTS[len(cast)], strict=True)),
            "card": name, "lead_seconds": scene["lead_seconds"],
            "tail_seconds": scene["tail_seconds"], "dialogue": dialogue,
        })
    return validate_plan({
        "episode": episode["id"], "title": episode["title"],
        "minimum_seconds": episode["duration_seconds"], "cards": cards, "scenes": scenes,
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("episode", type=str.upper)
    parser.add_argument("--output", type=Path, help="Write the scene plan to this JSON path")
    parser.add_argument("--url", default="http://walter-llm:8080")
    args = parser.parse_args()
    season = json.loads((ROOT / "bible/S01-Artificially-Intelligent.json").read_text(encoding="utf-8"))
    episode = next((item for item in season["episodes"] if item["id"] == args.episode), None)
    if episode is None:
        parser.error(f"Unknown episode {args.episode}")
    path = args.output or ROOT / "episodes" / f"{args.episode}-scenes.json"
    if path.exists():
        parser.error(f"Output already exists: {path}")
    cast = (ROOT / "bible/characters.md").read_text(encoding="utf-8")
    feedback = ""
    for attempt in range(1, 4):
        try:
            print(f"Generating {args.episode}, attempt {attempt}", flush=True)
            plan = assemble(episode, request_scenes(args.url, episode, cast, feedback))
            break
        except (ValueError, ValidationError) as error:
            feedback = error.message if isinstance(error, ValidationError) else str(error)
            print(feedback, file=sys.stderr, flush=True)
        except HTTPError as error:
            parser.error(f"Model request failed: {error}\n{error.read(1000).decode(errors='replace')}")
        except OSError as error:
            parser.error(f"Model request failed: {error}")
    else:
        parser.error("No valid scene plan after three attempts")
    try:
        with path.open("x", encoding="utf-8") as output:
            output.write(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
    except OSError as error:
        parser.error(str(error))
    turns = [turn for scene in plan["scenes"] for turn in scene["dialogue"]]
    words = sum(len(turn["line"].split()) for turn in turns)
    print(f"{path}: {len(plan['scenes'])} scenes, {len(turns)} turns, {words} spoken words")


if __name__ == "__main__":
    main()
