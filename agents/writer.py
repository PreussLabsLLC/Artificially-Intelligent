"""Generate a review draft of S01E01 from the series bible and approved pilot."""

import argparse
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen

from jsonschema import validate

ROOT = Path(__file__).resolve().parents[1]
BEATS = ("setup", "escalation", "punchline", "outro")
TURN = {
    "type": "object",
    "properties": {
        "speaker": {"enum": ["Walter", "Kyle", "Susan"]},
        "line": {"type": "string", "minLength": 1, "maxLength": 170},
    },
    "required": ["speaker", "line"],
    "additionalProperties": False,
}
EXCHANGE = {"type": "array", "items": TURN}
ACTION = {"type": "string", "minLength": 1, "maxLength": 280}


def closed_object(fields):
    return {
        "type": "object",
        "properties": fields,
        "required": list(fields),
        "additionalProperties": False,
    }


DRAFT_SCHEMA = closed_object({
    "setup": closed_object({"action": ACTION, "dialogue": {**EXCHANGE, "minItems": 3}}),
    "escalation": closed_object({
        "action": ACTION,
        "after_exchange": EXCHANGE,
    }),
    "punchline": closed_object({"action": ACTION, "dialogue": {**EXCHANGE, "minItems": 3}}),
    "outro": closed_object({"action": ACTION, "dialogue": EXCHANGE}),
})


def request_draft(url, episode, cast):
    prompt = (
        "Write a short production screenplay draft for this animated office comedy. "
        "Follow the four source beats and keep their reveals in order. One office set, "
        "short playable actions, dry reactions, and concise spoken lines. The episode "
        "should run at least 60 seconds. Build enough action, dialogue, and reaction "
        "beats to sustain that runtime. Go longer when the scene earns it. "
        "Leave space for silent beats. "
        "In setup, Kyle boasts about the hardware and Walter questions the specs. "
        "Keep the price and cats out of setup entirely. "
        "The original pilot clip supplies the first three turns of escalation. Walter "
        "questions the workstation's cost and use, Kyle gives a euphemism for making "
        "cat pictures, and Walter calls them cats. The script inserts those turns automatically. "
        "Write only the continuation in after_exchange. Escalation should add a new joke "
        "about the volume or specificity of the cat pictures. Save Susan and any mention of "
        "revenue or paying customers for punchline. Susan must explicitly say the cat "
        "account is the company's only source of revenue. Paying for the hardware alone "
        "does not satisfy that reveal. "
        "End on Walter reluctantly generating kittens. "
        "Use the schema's action field as the beat's visible action, never a spoken line."
        f"\n\nCAST\n{cast}\n\nEPISODE OUTLINE\n{json.dumps(episode, ensure_ascii=False)}"
        f"\n\nOUTPUT SCHEMA\n{json.dumps(DRAFT_SCHEMA)}"
    )
    request = Request(
        url.rstrip("/") + "/v1/chat/completions",
        headers={"Content-Type": "application/json"},
        data=json.dumps({
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 3800,
            "temperature": 0.25,
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "episode_draft", "strict": True, "schema": DRAFT_SCHEMA,
            }},
        }).encode("utf-8"),
    )
    with urlopen(request, timeout=120) as response:
        completion = json.load(response)
    choice = completion["choices"][0]
    if choice["finish_reason"] == "length":
        raise ValueError("The model ran out of tokens before completing the draft")
    draft = json.loads(choice["message"]["content"])
    validate(draft, DRAFT_SCHEMA)
    return draft


def assemble(episode, draft, locked_exchange):
    scenes = []
    for beat in BEATS:
        source = next(item for item in episode["outline"] if item["beat"] == beat)
        scene = draft[beat]
        dialogue = locked_exchange + scene["after_exchange"] if beat == "escalation" else scene["dialogue"]
        scenes.append({
            "beat": beat,
            "reference_seconds": source["end_seconds"] - source["start_seconds"],
            "set": "office",
            "action": scene["action"],
            "dialogue": dialogue,
        })

    generated = [
        turn["line"].casefold()
        for scene in scenes
        for turn in (scene["dialogue"][len(locked_exchange):]
                     if scene["beat"] == "escalation" else scene["dialogue"])
    ]
    if any(turn["line"].casefold() in generated for turn in locked_exchange):
        raise ValueError("The writer repeated dialogue from the approved exchange")
    susan_dialogue = " ".join(turn["line"].casefold() for turn in scenes[2]["dialogue"]
                              if turn["speaker"] == "Susan")
    if not all(word in susan_dialogue for word in ("cat account", "only", "revenue")):
        raise ValueError("Susan must reveal the cat account is the only source of revenue")
    setup_lines = scenes[0]["action"] + " " + " ".join(turn["line"] for turn in scenes[0]["dialogue"])
    if re.search(r"\b(?:cats?|kittens?|felines?|dollars)\b|\$", setup_lines, re.I):
        raise ValueError("Setup gives away the workstation cost or the cat reveal")
    early_dialogue = scenes[0]["dialogue"] + scenes[1]["dialogue"]
    if any(turn["speaker"] == "Susan" or re.search(r"\brevenue\b", turn["line"], re.I)
           for turn in early_dialogue):
        raise ValueError("The revenue reveal belongs in the punchline")
    words = sum(len(re.findall(r"\b[\w’'-]+\b", turn["line"]))
                for scene in scenes for turn in scene["dialogue"])
    return {
        "episode": episode["id"],
        "title": episode["title"],
        "status": "draft",
        "minimum_seconds": episode["duration_seconds"],
        "spoken_words": words,
        "scenes": scenes,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--url", default="http://walter-llm:8080")
    args = parser.parse_args()
    season = json.loads((ROOT / "bible/S01-Artificially-Intelligent.json").read_text(encoding="utf-8"))
    episode = next(item for item in season["episodes"] if item["id"] == "S01E01")
    cast = (ROOT / "bible/characters.md").read_text(encoding="utf-8")
    pilot = json.loads((ROOT / "episodes/walter-kyle-pilot.json").read_text(encoding="utf-8"))
    exchange = [{"speaker": speaker, "line": take["line"]}
                for speaker, take in zip(("Walter", "Kyle", "Walter"), pilot["timing"], strict=True)]
    draft = assemble(episode, request_draft(args.url, episode, cast), exchange)
    with args.output.open("x", encoding="utf-8") as output:
        output.write(json.dumps(draft, ensure_ascii=False, indent=2) + "\n")
    print(f"{draft['episode']} {draft['title']} — {draft['spoken_words']} spoken words")


if __name__ == "__main__":
    main()
