# Progress — 2026-11-25
Completed: concept, twelve episode outlines, character design references, office and prop concept art. User selected black-and-white rig concept 3; subsequent color sheet uses a different layout, so reconcile against the selected design before locking production assets. No animation engine or voice tests yet.
Next: implement one production-ready Walter SVG rig and JSON pivot/layer definition, then a test bench for mouth shapes, blink, gaze and gestures. Prototype a short dialogue scene from S01E01 with Kyle after Walter works. Target 1920x1080 at 24 fps with limited animation at 8–12 fps. Proposed sets: main office, Walter lab, Susan office, conference room, server room, arcade break room. Separate foreground layers from backgrounds. Actual render timings and voice IDs remain untested.
Pilot dialogue: Walter: Five thousand dollars. For cats? Kyle: Synthetic feline content, Walter. Walter: They're cats, Kyle. End with silent stare and accelerating fans. Aim for about 10 seconds; adjust to synthesized speech.

## Walter milestone review — 2026-11-25

Reviewed the architecture, cast notes, twelve season outlines, selected character sheets, alternate concepts, and office/prop references. Use the selected black-and-white concept 3 for Walter's front silhouette, angular gray fringe, pointed collar, eye spacing, and short legs. Use the color sheet for the sweater blue, hair gray, warm skin, and charcoal trousers. Keep production SVGs separate from the reference PNGs and preserve the episode guide.

1. Draw a front-view master SVG with stable group IDs and a neutral pose. Split shoulders, elbows, wrists/hands, hips, knees and shoes. Give each eye, pupil, eyelid and brow its own control under the head, and make mouths and hand poses swappable at shared anchors.
2. Pair the SVG with a versioned JSON rig containing the viewBox, ground anchor, joint hierarchy, bind-pose pivots, back-to-front layer order, and variant IDs. Document character left/right and validate the JSON against the SVG before animating.
3. Build a deterministic Python test bench for isolated controls and a short acting sequence. Exercise blinks, side-eye, skeptical and surprised expressions, a point, a shrug and every mouth shape. Export stills and a 1920×1080, 24 fps preview, with body poses held at 12 fps and speech cues sampled on the output frame grid. Review joint seams, pupil clipping, and the return to Walter's neutral stare.
4. Test lip timing with a small Rhubarb-format fixture before connecting real speech. Then audition Kokoro voices for Walter's mature, dry delivery, synthesize “Five thousand dollars. For cats?”, and import Rhubarb's timestamped mouth cues using the transcript. Map A–F and extended G/H/X to SVG variants and check closures, pauses, and sound/video alignment. Keep generated media and weights out of Git.

Verified on Windows: Python 3.14.5, uv 0.8.15, and FFmpeg 7.1 are callable. Rhubarb was not found on Windows PATH. The sandboxed WSL inventory returned `Wsl/E_ACCESSDENIED`, so Ubuntu tooling and GPU access are unverified. Kokoro and Ollama were not exercised. Upstream documentation identifies [Kokoro-82M weights as Apache-2.0](https://huggingface.co/hexgrad/Kokoro-82M) and [Rhubarb as MIT](https://raw.githubusercontent.com/DanielSWolf/rhubarb-lip-sync/master/LICENSE.md). Runtime compatibility, the selected voice, and actual render and lip-sync timings remain open. This entry records review and planning only.
## santa-dev environment inventory

Connected to the running Linux x86-64 container with approved Docker access. It reports Ubuntu 24.04.5, Python 3.12.3, uv 0.11.28, and FFmpeg 6.1.1. The RTX 3090 is visible to `nvidia-smi`, and FFmpeg lists libx264 and H.264 NVENC. Actual encoding and CUDA inference were not tested.

Python discovers Pillow, Torch, Kokoro, and jsonschema. eSpeak NG and the Cairo, librsvg, and libsndfile runtime libraries are installed. Suggested additions for Walter are `librsvg2-bin` for the headless SVG renderer, Python `soundfile` in the project uv environment for Kokoro WAV output, and a pinned upstream Rhubarb Linux x86-64 release. The renderer CLI, Rhubarb, and Git were absent from PATH. No packages were installed during this inventory.

## santa-dev dependency setup

Installed Ubuntu `librsvg2-bin` (renderer 2.58.0), `soundfile==0.14.0` via `uv pip` into the container's existing Kokoro Python environment, and [Rhubarb Lip Sync 1.14.0](https://github.com/DanielSWolf/rhubarb-lip-sync/releases/tag/v1.14.0) under `/opt/Rhubarb-Lip-Sync-1.14.0-Linux`, exposed as `/usr/local/bin/rhubarb`. Verified the user-installed Git 2.43.0. These installs are in the running container's writable layer.

From `/data/Artificially-Intelligent`, rendered a test SVG to PNG and checked its pixel output, generated a spoken WAV with eSpeak NG, read and rewrote it with SoundFile, extracted 12 JSON mouth cues with Rhubarb, and verified the FFmpeg output carried H.264 and AAC streams. Kokoro's `KPipeline` imported successfully. Kokoro synthesis, voice selection, and NVENC encoding remain untested. Smoke-test media was generated in a temporary container directory and cleaned up.

## Walter voice audition

Synthesized “Five thousand dollars. For cats?” on CPU in `santa-dev` with Kokoro-82M. Used `am_michael` as an audition voice at 0.93× speed and inserted 300 ms of silence between clauses. Saved the 4.35-second, 24 kHz mono PCM WAV as `walter-voice-test.wav` in the mapped workspace. Rhubarb generated 17 mouth cues with the transcript. The voice and delivery are open for review.

## Animated Walter pilot shot

Used the approved voice take with a new front-facing SVG cutout based on the selected silhouette and color references. The shot includes a simple office set, Rhubarb-driven mouth shapes, a blink, a head tilt and a small arm gesture, followed by a silent reaction. The shot-specific renderer is `engine/render_walter.py`. From the mapped project directory in `santa-dev`, rendered with `python3 engine/render_walter.py walter-voice-test.wav walter-animated.mp4`.

Verified the 5.625-second output with FFprobe (1920×1080, 24 fps, H.264 video and AAC audio), inspected a frame during the question, and confirmed the MP4 is Git-ignored.

## Local LLM cache inventory

With the Mac mini out of the workflow for now, inspected `/cache/huggingface/hub` in `santa-dev`. The candidate for both writer and director is the cached `unsloth/gpt-oss-20b-GGUF` snapshot `d449b42d93e1c2c7bda5312f5c25c8fb91dfa9b4`, which resolves `gpt-oss-20b-F16.gguf` to 13,792,639,168 bytes. The RTX 3090 reported 23,231 MiB free out of 24,576 MiB. `llama-cli`, `llama-server`, and `ollama` were absent from PATH. Model loading and generation are untested.

## Local GPT-OSS director smoke test

Started `walter-llm` beside `santa-dev` with the CUDA llama.cpp image pinned to `sha256:2855fd7d0f5781e289a8108c3abd0744d19621314641b97421c038be836ed373`. It reads the existing GGUF from a read-only bind mount, with 8,192 tokens of context and one inference slot. Startup succeeded with `--load-mode none` after the default memory-mapped startup stayed in loading. The runtime reported CUDA offload of 25/25 layers and a 12,036.68 MiB GPU model buffer. The endpoint is `http://walter-llm:8080` from `santa-dev` on the `walter-pipeline` Docker network, and `http://127.0.0.1:18080` from Windows.

Ran `docker exec -w /data/Artificially-Intelligent santa-dev python3 tests/check_walter_director.py`. GPT-OSS preserved the approved dialogue and generated a brow raise before the question, a blink on it, and a silent stare after the line. The output passed JSON Schema and cue-order checks. The server reported 1.72 seconds of inference on this request. The animation renderer still uses the hand-authored shot. Writer quality and rendering from model-generated plans remain untested.

## Model-directed Walter render

Generated `episodes/walter-directed.json` with `python3 tests/check_walter_director.py --output episodes/walter-directed.json` in `santa-dev`. The director test and renderer share the shot schema. Rendered with `python3 engine/render_walter.py walter-voice-test.wav walter-directed.mp4 --shot episodes/walter-directed.json`. Without `--shot`, the renderer uses the original acting. For the model-directed take, the end of the longest interior Rhubarb rest anchors the question, and the start of the final rest anchors the held stare.

Created `walter-comparison.mp4` with the original on the left and the GPT-OSS take on the right. Inspected frames before, during, and after the question. The new take preserves the pause and moves from a brow raise to a blink on the question, then holds the stare through the end. It uses fewer gestures than the original. FFprobe verified both takes are 1080p at 24 fps and 5.625 seconds. The decoded audio SHA-256 hashes match across both takes and the comparison. Both generated videos are Git-ignored.

## Walter and Kyle pilot exchange

Added Kyle's front-facing SVG cutout from the cast references and shared the existing Walter cutout and office with `engine/render_pilot.py`. Reused the approved opening WAV, auditioned Kokoro `am_fenrir` at 1.07× for Kyle, and used Walter's `am_michael` at 0.93× for the closing line. Rhubarb found speech at 0.39–3.88, 4.56–6.35, and 7.23–8.34 seconds. GPT-OSS supplied speaker and listener actions for each line, including Walter's brow raise during Kyle's explanation and Kyle's blink on Walter's reply. Walter's final stare and the rising synthesized fan are scripted ending beats. Saved the model's actions and measured timing in `episodes/walter-kyle-pilot.json`.

Rendered in `santa-dev` with `python3 engine/render_pilot.py walter-voice-test.wav walter-kyle-pilot.mp4 --plan episodes/walter-kyle-pilot.json`. FFprobe verified 1920×1080 H.264 at 24 fps with AAC audio and about 10 seconds of runtime. FFmpeg decoded the whole clip without errors. Inspected frames of both listener reactions and the closing stare. A fresh render of the original Walter shot matched its previous decoded video and audio hashes. The pilot MP4 is Git-ignored. Kyle's voice is an audition choice.

Adjusted Kyle's SVG head silhouette to sit under the hair spikes. A fresh synthesis shifted the approved timing, so applied a mask derived from the SVG change to the original cut and copied its AAC stream into `walter-kyle-hair-fixed.mp4`. Verified a matching AAC bitstream hash, 239 video frames at 24 fps with the same duration, and inspected close-ups with Kyle's eyes open and blinking.

## Pilot performance replay

The pilot renderer can now capture a new take with `python3 engine/render_pilot.py walter-voice-test.wav take.mp4 --plan take.json --record take.performance.zip`. The archive holds the mixed WAV, full Rhubarb cue timeline, chosen actions, and closing beat. For a visual revision, use `python3 engine/render_pilot.py revision.mp4 --plan revision.json --replay take.performance.zip`. Generated performance archives with this suffix are Git-ignored.

Recorded and replayed a fresh take in a temporary directory in `santa-dev`. Replay succeeded with an unreachable model URL and no opening WAV input. The emitted plans and decoded video and audio SHA-256 hashes matched. The approved hair-fixed cut predates performance capture and remains the review copy.

## S01E01 writer draft

Added `agents/writer.py` to send the original S01E01 outline and cast notes to local GPT-OSS and assemble schema-constrained output. The approved Walter–Kyle exchange is inserted verbatim from the pilot plan. Early generations ran short, duplicated dialogue, or revealed plot points too early. Added checks for these cases and tightened the prompt. The selected model draft needed one editorial correction to make Susan's only-source-of-revenue reveal explicit.

Validated the resulting `episodes/S01E01-draft.json` in `santa-dev` against the writer schema and story checks. Independently compared the approved dialogue with the pilot plan and verified four beat targets sum to 60 seconds. The draft has 96 spoken words. Full-episode read-through and measured duration are pending.

The user clarified that 60 seconds is the episode floor. Updated the project objective, writer prompt, and draft metadata to use `minimum_seconds`. The source outline's beat durations are carried forward as `reference_seconds`. Removed the writer's dialogue count and spoken word caps. In `santa-dev`, verified the current 96-word draft round-trips through the writer and a 168-word fixture passes the updated schema and story checks.

## S01E01 voice read-through

Rendered `S01E01-table-read.wav` locally with Kokoro, reusing the three-line exchange audio from the approved hair-fixed pilot. New lines use `am_michael` at 0.93× for Walter and `am_fenrir` at 1.07× for Kyle. Auditioned `af_nicole` at 0.95× for Susan and exported her reveal as `susan-voice-audition.wav`. SoundFile verified both as 24 kHz mono PCM WAVs, with durations of 51.63 seconds for the read-through and 4.94 seconds for Susan. This is a dialogue read with short pauses. The episode's 60-second floor applies to the finished cut with staged action and reactions.

## Susan Australian-English voice audition

Rendered Susan's reveal on CPU with Piper 1.8.0 in an isolated `uv run` environment. Used Data Craftsman's [Australian English multi-speaker model](https://huggingface.co/DataCraftsmanAustralia/piper-en_AU-librivox-medium) (CC BY 4.0), downloaded to the shared Hugging Face cache. Marlo (speaker 2, length scale 1.08) runs 3.23 seconds. Bindi (speaker 1, length scale 1.04) runs 2.77 seconds. Both are Git-ignored 22.05 kHz mono PCM WAVs and decoded successfully with FFmpeg. These are auditions for Susan's voice.

The user approved Marlo. Recorded the approved voice and settings in `bible/characters.md`. The existing table read predates the selection and uses the earlier Kokoro audition for Susan.

## Animated Susan reveal

Added a front-facing Susan cutout with the reference dark bob, purple sweater and white collar. Staged the three characters in the office. Susan raises a revenue sheet, the board shows the cat account at 100%, Kyle perks up, and Walter reacts late. The acting was staged by hand for this shot. Reused the exact approved `susan-australian-marlo.wav` as the source and saved the source hash, 17 Rhubarb mouth cues and acting times in `episodes/susan-reveal.json`.

Rendered in `santa-dev` with `python3 engine/render_susan.py susan-australian-marlo.wav susan-reveal.mp4 --shot episodes/susan-reveal.json`. FFprobe reported 133 frames, 1920×1080 at 24 fps, and AAC audio. Inspected the reveal and final reaction. Replayed from the saved cues and original WAV and verified identical decoded video and audio hashes.

## Walter Southern US drawl audition

Used Walter's existing Kokoro `am_michael` voice and the same pilot line. Tested a flatter vowel on “five” (`fˈɑv` in Kokoro's phoneme input), a slightly slower delivery at 0.89× and 0.90×, and the original 300 ms inserted pause. Saved `walter-southern-audition.wav` as a separate 4.40-second take and verified 14 Rhubarb cues. The audition is pending review.

The user rejected that audition and asked for a Tim Cook-style delivery. Rendered `walter-keynote-audition.wav` with `am_michael`, default pronunciation, a 650 ms explicit pause, a softer question, and slight reduction around 3.4 kHz. Verified it is a finite, unclipped 3.44-second mono 24 kHz PCM WAV. The keynote audition is pending review.

The user approved the keynote take. Recorded the reference WAV and reproducible delivery settings in `bible/characters.md`. Existing pilot visuals still use their original timed recording.

## S01E01 animatic dialogue track

Added `engine/render_table_read.py` and rendered `S01E01-animatic-audio.wav` in `santa-dev` with `--timing episodes/S01E01-animatic-timing.json`. Used Walter's approved keynote take, Kyle's line from the approved pilot, and Susan's approved Marlo reveal. Synthesized the remaining Walter and Kyle lines with their established voices. The timing file includes sample ranges for dialogue and named action holds. Where needed, distributed time across the visual holds to reach the 60-second episode floor.

Verified 12 spoken lines in screenplay order, nonoverlapping cue ranges, silent action holds, a sample-for-sample match for Walter's approved opening WAV, and 1,440,000 total samples at 24 kHz. The track is a dialogue and timing reference for the animatic. The action holds are ready for images and sound design.

## S01E01 full animatic

Rendered `S01E01-animatic.mp4` in `santa-dev` with `engine/render_animatic.py`, the saved dialogue WAV and timing JSON, and `--cues episodes/S01E01-animatic-cues.json`. Staged the four beats with the existing cutouts and office, adding the workstation tower, cat gallery, Susan's revenue board, and the kitten result. Acting and screen changes are hand-staged for this cut. A synthesized fan spins up during the closing hold. Rhubarb ran per line and the renderer saved all 12 cue lists with the source hashes so they can be reused on visual revisions.

FFprobe verified 1,440 frames at 24 fps, 1920×1080 H.264, and 60.00 seconds of video and AAC audio. FFmpeg decoded the complete file without errors. Inspected a frame from each beat, verified both source hashes and all 12 dialogue cue lists, and confirmed the MP4 is Git-ignored.

Moved Susan 32 SVG units right in the punchline shot to leave a clear gap beside Kyle. Reused the saved lip-sync cues to render `S01E01-animatic-revised.mp4`. Inspected the updated reveal frame, confirmed identical AAC bitstream hashes, and verified both cuts have 1,440 frames at 24 fps and a 60.00-second video duration.
