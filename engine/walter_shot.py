"""Shared schema for the Walter pilot shot and its acting cues."""

from jsonschema import validate

LINE = "Five thousand dollars. For cats?"
ACTION_IDS = ["blink", "head_tilt", "raise_brow", "arm_gesture", "hold_stare"]
ANCHORS = ["before_question", "on_question", "after_line"]
SCHEMA = {
    "type": "object",
    "properties": {
        "character": {"const": "walter"},
        "set": {"const": "office"},
        "dialogue": {"const": LINE},
        "cues": {
            "type": "array",
            "minItems": 2,
            "maxItems": 5,
            "items": {
                "type": "object",
                "properties": {
                    "action": {"enum": ACTION_IDS},
                    "anchor": {"enum": ANCHORS},
                },
                "required": ["action", "anchor"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["character", "set", "dialogue", "cues"],
    "additionalProperties": False,
}


def validate_shot(shot):
    validate(instance=shot, schema=SCHEMA)
    cues = shot["cues"]
    order = [ANCHORS.index(cue["anchor"]) for cue in cues]
    if order != sorted(order):
        raise ValueError("Acting cues are out of order")
    if cues[-1] != {"action": "hold_stare", "anchor": "after_line"}:
        raise ValueError("The final cue must hold the stare after the line")
    if any(cue["action"] == "hold_stare" for cue in cues[:-1]):
        raise ValueError("The held stare must appear only as the final cue")
    if not any(cue["anchor"] == "on_question" for cue in cues[:-1]):
        raise ValueError("The question is missing an acting cue")
