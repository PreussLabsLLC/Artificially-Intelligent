# Artificially Intelligent
A one-minute episodic AI startup satire. See `capstone.md` for the architecture, `bible/` for the cast and season, `assets/reference/` for original artwork, and `progress.md` for production notes.

## Start an episode render

Run `python3 engine/produce_episode.py S01E02` from the project directory in the Linux production environment. From Windows PowerShell, use the existing container:

```powershell
docker exec -w /data/Artificially-Intelligent santa-dev python3 engine/produce_episode.py S01E02 --output output/S01E02-new-cut.mp4
```

The command supports the original S01E01 and S01E02 renderers and discovers scene plans named `episodes/SxxEyy-scenes.json`. Omit `--output` to use the episode's standard filename for a first render. An existing export is protected from replacement.

## S01E01 — Return on Investment

The approved 60-second animatic is at `output/S01E01-Return-On-Investment.mp4` in the production workspace. To rebuild it from the saved lip-sync cues and approved recordings, run this from the project directory in the existing Linux production environment:

```sh
python3 engine/produce_episode.py S01E01
```

Use `--output` to render a second copy while keeping the approved export. The renderer uses NumPy, SoundFile, librsvg's `rsvg-convert`, and FFmpeg. Keep a local backup of `S01E01-animatic-four-gpus-audio.wav` at the project root and the three approved MP3s in `assets/music/` with their original filenames. These audio files are Git-ignored. The renderer verifies the input hashes, and the adjacent music JSON files record the generation settings.

The final MP4 includes selectable English, standard German, and neutral Latin American Spanish subtitles, with English marked as the default. The render command embeds the editable SRT files from `episodes/subtitles/`.

## S01E02 — Chief Executive Algorithm

The episode export is `output/S01E02-Chief-Executive-Algorithm.mp4`. Its scene draft and translated dialogue are in `episodes/S01E02-draft.json`. To render from the local production environment:

```sh
python3 engine/produce_episode.py S01E02
```

The renderer uses the same local music assets as S01E01, the approved `review/S01E02-Chip-audition.mp4` for the closing shot, and Susan’s Marlo Piper checkpoint in the shared Hugging Face cache. It synthesizes the voices locally and embeds English, German, and Latin American Spanish subtitles. A render to the standard episode filename also writes SRTs to `episodes/subtitles/`.

## Scene-plan production

S01E03 is the first episode produced from a scene plan. Run `python3 engine/produce_episode.py S01E03` in the Linux production environment, or use the Docker command above with `S01E03` in PowerShell. The standard export is `output/S01E03-Hallucination-as-a-Service.mp4`.

Use `episodes/S01E03-scenes.json` as the template for another office episode. Define the episode ID, title, runtime floor, monitor cards, and ordered scenes. Each scene specifies its cast and horizontal positions, the opening card, opening and closing holds, and turns with a speaker, English dialogue, and German and Spanish translations. A turn can set acting directions for speakers and listeners and reveal a new monitor card after a delay measured from the start of its line. The current renderer supports the office set and the four established cast members. It uses the existing local voices, music, and lip-sync tools and writes three selectable subtitle tracks.

## Generate a scene plan from the season outline

With the local GPT-OSS server running, generate one office episode from the season bible. These commands run from Windows PowerShell with the existing production container.

```powershell
docker exec -w /data/Artificially-Intelligent santa-dev python3 agents/generate_scene_plan.py S01E04
docker exec -w /data/Artificially-Intelligent santa-dev python3 engine/produce_episode.py S01E04 --output review/S01E04-new-cut.mp4
```

The generator writes `episodes/S01E04-scenes.json` by default, which the production command discovers automatically. The S01E04 trial plan is already in that location, so you can run the render command directly. The generator uses the outline's title and runtime floor and generates dialogue, German and Latin American Spanish translations, acting cues, and monitor cards. Read the generated plan to review the story beats, dialogue, and translations before promoting a cut. Use `--output` on the generator to save an alternate JSON and pass that file directly to `engine/render_scene_plan.py`. Existing files are protected from replacement. Use `--url` to override the default model endpoint at `http://walter-llm:8080`.
