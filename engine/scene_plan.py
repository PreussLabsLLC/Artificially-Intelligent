"""Shared scene-plan vocabulary and validation."""

import json
import re


OFFICE = "office"
ACTIONS = {
    "Walter": {"raise_brow", "stare", "gesture"},
    "Kyle": {"present", "nod", "raise_brow"},
    "Susan": {"present"},
    "Chip": {"thinking"},
}


def read_plan(path):
    return validate_plan(json.loads(path.read_text(encoding="utf-8")))


def validate_plan(plan):
    if not re.fullmatch(r"S\d{2}E\d{2}", plan["episode"]) or not plan["scenes"]:
        raise ValueError("A scene plan needs an episode ID and at least one scene")
    for index, scene in enumerate(plan["scenes"], 1):
        cast = scene["cast"]
        if scene["set"] != OFFICE or not cast or cast.keys() - ACTIONS.keys():
            raise ValueError(f"Unknown set or cast in scene {index}")
        if scene["card"] not in plan["cards"] or not scene["dialogue"]:
            raise ValueError(f"Scene {index} needs a known opening card and dialogue")
        for turn in scene["dialogue"]:
            if turn["speaker"] not in cast or any(not turn[key].strip() for key in ("line", "de", "es")):
                raise ValueError(f"Invalid speaker or missing dialogue or translation in scene {index}")
            for actor, action in turn.get("acting", {}).items():
                if actor not in cast or action not in ACTIONS[actor]:
                    raise ValueError(f"Unknown action {action!r} for {actor} in scene {index}")
            screen = turn.get("screen")
            if screen and (screen["card"] not in plan["cards"] or screen["after"] < 0):
                raise ValueError(f"Invalid screen cue in scene {index}")
    return plan
