# Artificially Intelligent
A one-minute episodic AI startup satire. See `capstone.md` for the architecture, `bible/` for the cast and season, `assets/reference/` for original artwork, and `progress.md` for production notes.

## Start an episode render

Run `python3 engine/produce_episode.py S01E02` from the project directory in the Linux production environment. From Windows PowerShell, use the existing container:

```powershell
docker exec -w /data/Artificially-Intelligent santa-dev python3 engine/produce_episode.py S01E02 --output output/S01E02-new-cut.mp4
```

The command supports the original S01E01 and S01E02 renderers and discovers scene plans named `episodes/SxxEyy-scenes.json`. Omit `--output` to use the episode's standard filename for a first render. An existing export is protected from replacement.

Scene-plan renders transcribe each dry dialogue take before lip sync with faster-whisper's English `small.en` model on CPU by default. Pass `--no-check-dialogue` to skip the check. The first run with checking enabled needs access to PyPI and Hugging Face to populate the uv and model caches. Later runs can use the cached model offline. The check prints the time, speaker, script and transcript when the words differ, including possible false positives such as numbers written in a different form. It flags lines for listening and lets the render continue. Check the finished mix by ear for music masking, delivery and voice consistency.

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

## Watch episodes in the browser

From Windows PowerShell, build an episode with the existing production container. The exporter accepts episode IDs S01E01 through S01E05 or a path to a scene-plan JSON file.

```powershell
docker exec -w /data/Artificially-Intelligent santa-dev python3 engine/export_web_episode.py S01E01
```

Open `web-build/index.html` directly in a browser, or open an episode’s own `index.html` to watch it on its own. Keep the accompanying files together. Run this command to serve the season over HTTP.

```powershell
python -m http.server 8000 --bind 127.0.0.1 --directory web-build
```

Choose a generated episode from the season index. The index uses the season bible and labels episodes awaiting a browser export as pending. In the player, use the CC selector for English, German, Latin American Spanish, or Off. S01E01 uses the approved dialogue WAV, saved mouth cues, and approved subtitle timings, with the closing fan generated by the animatic mixer. S01E02 synthesizes the draft and rebuilds the closing audition using its original staging. Scene-plan episodes synthesize fresh performances with the installed Kokoro and Piper voices and Rhubarb timings. All five use FFmpeg and the approved local music files. Use `--output` for a separate build and `--no-check-dialogue` to skip transcription checking for scene-plan episodes.

Each generated episode folder is a standalone static site with page-relative URLs. For GitHub Pages, upload the **contents** of `web-build/` for the season index and its episodes, or the **contents** of an episode folder for a single episode. Include `.nojekyll` in either case. The build output is Git-ignored and can be generated in the production environment before deployment. The player draws native SVG and uses an audio-only soundtrack to keep the scene, expressions, gestures, blinks, mouth shapes and captions in sync.

## Generate a scene plan from the season outline

With the local GPT-OSS server running, generate one office episode from the season bible. These commands run from Windows PowerShell with the existing production container.

```powershell
docker exec -w /data/Artificially-Intelligent santa-dev python3 agents/generate_scene_plan.py S01E04
docker exec -w /data/Artificially-Intelligent santa-dev python3 engine/produce_episode.py S01E04 --output review/S01E04-new-cut.mp4
```

The generator writes `episodes/S01E04-scenes.json` by default, which the production command discovers automatically. The S01E04 trial plan is already in that location, so you can run the render command directly. The generator uses the outline's title and runtime floor and generates dialogue, German and Latin American Spanish translations, acting cues, and monitor cards. Read the generated plan to review the story beats, dialogue, and translations before promoting a cut. Use `--output` on the generator to save an alternate JSON and pass that file directly to `engine/render_scene_plan.py`. Existing files are protected from replacement. Use `--url` to override the default model endpoint at `http://walter-llm:8080`.
