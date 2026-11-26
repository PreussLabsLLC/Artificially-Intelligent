# Capstone: AI-Powered Cartoon Studio

## Objective

Build a predominantly local, automated animation studio that produces comedy episodes of at least 60 seconds from a short premise, with consistent original characters, LLM-generated storylines, dialogue, lip-sync, background music and sound effects. Let episodes run longer when the pacing calls for it. The visual inspiration is South Park's limited 2D paper-cutout animation, with an original cast and visual identity.

Use AI to generate assets and direct episodes, but conventional programmatic animation to preserve character consistency. Reserve generative video for special sequences.

## 1. Production pipeline

1. **Writer:** LLM generates storyline, jokes and dialogue.
2. **Director:** Converts screenplay into shots, actions and camera angles.
3. **Art department:** Supplies reusable character rigs, backgrounds and props.
4. **Voice studio:** Synthesizes consistent character voices and timed dialogue.
5. **Animation engine:** Executes movement, expressions and lip-sync.
6. **Sound department:** Selects or generates music, ambience and effects.
7. **Editor:** Composites, mixes, adds subtitles and renders MP4.

Each department can become an independent AI agent or deterministic Python module, exchanging structured JSON.

## 2. Visual approach

- Flat colors, simple shapes, limited movement and reusable cutout assets.
- Character sprite sheets with interchangeable mouths, eyes, expressions, limbs and poses.
- Reusable sets: offices, living rooms, streets and restaurants.
- Storyboard-driven wide shots, close-ups, reaction shots and comic timing.

Generate character assets once and reuse them across episodes rather than asking a video model to recreate them in each clip.

## 3. Recommended software stack

| Production task | Software/model | Hardware |
|---|---|---|
| Story and dialogue | Qwen / GPT-OSS | Mac mini |
| Screenplay and directing | LLM with structured JSON | Mac mini |
| Character design | FLUX / Qwen-Image | RTX 3090 |
| Background generation | FLUX / Stable Diffusion XL | RTX 3090 |
| Character voices | Kokoro-82M / F5-TTS | RTX 3090 |
| Lip synchronization | Rhubarb Lip Sync | CPU |
| Cutout animation | Python, Pillow, Skia | CPU |
| Special video sequences | Wan 2.2 | RTX 3090 |
| Background music | ACE-Step / MusicGen | RTX 3090 |
| Sound effects | AudioLDM 2 | RTX 3090 |
| Audio mixing | FFmpeg / Pydub | CPU |
| Final rendering | FFmpeg / NVENC | RTX 3090 |

Target environment: existing Mac mini with local LLMs and Windows workstation with WSL, Python, uv and RTX 3090 (24 GB VRAM).

### Existing projects to investigate

- [Synctoon](https://github.com/Automate-Animation/synctoon): LLM-directed cutout animation.
- [AN](https://github.com/reeleehq/an): structured AI-driven animation in Python.
- [Rhubarb Lip Sync](https://github.com/DanielSWolf/rhubarb-lip-sync): timed cartoon mouth shapes from speech.
- [PyToon](https://github.com/lukerbs/pytoon): programmatic cartoon animation driven by audio.

These are investigation candidates, not tested dependencies. Verify availability, compatibility and licensing before adoption, particularly for commercial distribution.

## 4. Consistent characters

Example original series: three people running a dysfunctional technology startup.

| Character | Personality | Voice | Signature expression |
|---|---|---|---|
| Walter, engineer | Sarcastic, competent, impatient | Mature, low-pitched, dry | Disapproving |
| Kyle, entrepreneur | Enthusiastic, overconfident, addicted to AI buzzwords | Youthful, fast, energetic | Exaggerated optimism |
| Susan, accountant | Pragmatic, unimpressed, voice of reason | Calm, precise, deadpan | Raised eyebrow |

Each character has a permanent identity, voice, personality, relationships and graphical assets defined in JSON.

### Character rig

Separate layers for hair, head, eyes/pupils, eyebrows, mouth, torso, arms/hands and legs/shoes. Include interchangeable visemes for rest, A/I, E, O, U, M/B, F/V and L; map these to the actual lip-sync engine's mouth-shape vocabulary.

Animation primitives: `idle`, `talk`, `blink`, `walk`, `nod`, `shake_head`, `shrug`, `point`, `angry`, `laugh`, `facepalm`, `eye_roll`.

## 5. Automated episode production

Example premise: Walter discovers that their new $5,000 AI workstation is being used exclusively to generate cat pictures.

### Episode 001: Return on Investment

| Time | Beat | Action |
|---|---|---|
| 00–05 s | Opening | Startup office; workstation fans roaring. |
| 05–17 s | Setup | Kyle proudly announces their new AI infrastructure. |
| 17–30 s | Discovery | Walter examines the generated cat pictures. |
| 30–44 s | Escalation | Kyle explains that the cats are a strategic investment. |
| 44–56 s | Punchline | Susan reveals that the cats have more followers than the company. |
| 56–60 s | Outro | Walter stares into the camera; musical sting. |

The director produces machine-executable scene descriptions:

```json
{
  "scene": 3,
  "duration": 6.5,
  "background": "startup_office",
  "camera": "medium_closeup",
  "characters": [
    {"id": "walter", "position": [0.3, 0.8], "expression": "annoyed", "action": "point"},
    {"id": "kyle", "position": [0.7, 0.8], "expression": "proud"}
  ],
  "dialogue": [
    {"speaker": "walter", "text": "Five thousand dollars. For cats?", "emotion": "incredulous", "start": 0.5}
  ],
  "sound_effects": [
    {"asset": "computer_fan", "start": 0, "volume": 0.2}
  ]
}
```

Finalize scene durations after speech synthesis, rather than relying on LLM estimates. The renderer simply executes the validated instructions.

## 6. Speech, music and sound effects

- **Speech:** Start with lightweight Kokoro. Investigate F5-TTS for more distinctive reference-based voices. Use original or authorized reference voices.
- **Lip-sync:** Analyze dialogue WAV files with Rhubarb to generate timed mouth shapes. Animate the speaking character independently.
- **Music:** Generate reusable opening and closing themes, incidental music and comedic stings with ACE-Step or MusicGen.
- **Sound effects:** Generate or acquire reusable doors, footsteps, computer noises, telephone rings and ambient backgrounds using AudioLDM 2 or licensed libraries.

Maintain four independent audio tracks: dialogue, music, sound effects and ambience. Automatically duck music during dialogue and accentuate punchlines with effects.

## 7. Generative video versus programmatic cutout

Recent Wan experiments averaged approximately five minutes per 81-frame clip. At an assumed 16 FPS, a minute of footage would take roughly an hour of GPU processing before retries and editing.

| Feature | Generative video | Programmatic cutout |
|---|---|---|
| Character consistency | Variable | Exact asset reuse |
| Lip-sync | Challenging | Deterministic |
| Multiple characters | Challenging | Straightforward |
| Repeatable scenes | Difficult | Exact |
| Editing individual actions | Difficult | Easy |
| Rendering time | Relatively high | Relatively low |
| GPU requirements | High | Low |
| Creative motion | Excellent potential | Limited to available animations |
| Automated series production | Complex | Well suited |

Use Wan selectively for dream sequences, dramatic flashbacks, explosions and other special scenes.

## 8. Estimated production time per episode

Target: approximately 3–8 minutes for a 60-second episode once the reusable asset library exists.

| Stage | Estimated time |
|---|---:|
| Story and direction | 15–60 s |
| Speech generation | 10–30 s |
| Lip-sync analysis | 5–15 s |
| Timeline compilation | 1–5 s |
| Animation rendering | 60–180 s |
| Music and SFX selection | 5–15 s |
| Final mixing and encoding | 10–30 s |

These are engineering targets, not measured benchmarks. They exclude initial asset creation, review, retries and diffusion video generation.

## 9. Proposed project structure

```text
ai-cartoon-studio/
├── bible/
│   ├── universe.md
│   ├── characters.json
│   ├── writing_style.md
│   └── continuity.json
├── assets/
│   ├── characters/
│   ├── backgrounds/
│   ├── props/
│   ├── voices/
│   ├── music/
│   └── sfx/
├── agents/
│   ├── writer.py
│   ├── director.py
│   └── continuity.py
├── engine/
│   ├── speech.py
│   ├── lipsync.py
│   ├── animation.py
│   ├── compositor.py
│   └── audio.py
├── episodes/
│   └── e001/
│       ├── premise.txt
│       ├── screenplay.json
│       ├── timeline.json
│       ├── audio/
│       └── episode.mp4
└── produce.py
```

Example production command:

```bash
uv run python produce.py \
  --premise "The AI intern accidentally becomes CEO" \
  --duration 60 \
  --episode 002
```

The series bible maintains continuity across episodes, including running gags, previous events and evolving relationships.

## 10. Implementation roadmap

| Phase | Deliverable |
|---|---|
| 1 | One character speaking with synchronized mouth movements |
| 2 | Two characters conversing in a fixed setting |
| 3 | Expressions, gestures, camera cuts and reaction shots |
| 4 | LLM-generated screenplay and automated directing |
| 5 | Music, sound effects and audio mixing |
| 6 | Fully automated one-minute episodes |
| 7 | Persistent series continuity and occasional generative video |

### Minimum viable prototype

Avoid diffusion models initially. Two simple characters, one office background, Kokoro, Rhubarb, Pillow and FFmpeg are sufficient to demonstrate the concept. Introduce AI-generated artwork and more sophisticated animation after the core pipeline works.

### Conclusion

Combine generative AI with traditional software engineering to build a virtual animation studio whose components are replaceable, testable and independently improvable. The existing Mac mini and RTX 3090 workstation provide a suitable starting platform without requiring additional hardware.
