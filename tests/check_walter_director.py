"""Check that the local model can plan Walter's pilot shot."""

import argparse
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen

# Keep the smoke test runnable as a script from the mapped checkout.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.walter_shot import LINE, SCHEMA, validate_shot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://walter-llm:8080")
    parser.add_argument("--output", type=Path, help="Save the validated shot plan")
    args = parser.parse_args()
    request = Request(
        args.url.rstrip("/") + "/v1/chat/completions",
        headers={"Content-Type": "application/json"},
        data=json.dumps({
            "messages": [{
                "role": "user",
                "content": (
                    "Direct a single office shot of Walter, a dry, skeptical veteran engineer. "
                    f"He says exactly: {LINE} "
                    "Use the allowed cutout actions to show his disbelief on the question. "
                    "End with a silent stare. Place each action relative to the dialogue, "
                    "in chronological order. Keep his performance restrained. "
                    f"Return only the shot matching this JSON schema: {json.dumps(SCHEMA)}"
                ),
            }],
            "temperature": 0,
            "max_tokens": 768,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "walter_shot", "strict": True, "schema": SCHEMA},
            },
        }).encode(),
    )
    with urlopen(request, timeout=120) as response:
        completion = json.load(response)
    shot = json.loads(completion["choices"][0]["message"]["content"])
    validate_shot(shot)
    formatted = json.dumps(shot, indent=2) + "\n"
    if args.output:
        args.output.write_text(formatted, encoding="utf-8")
    print(formatted, end="")


if __name__ == "__main__":
    main()
