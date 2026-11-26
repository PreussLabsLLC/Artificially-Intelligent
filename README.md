# Artificially Intelligent
A one-minute episodic AI startup satire. See `capstone.md` for the architecture, `bible/` for the cast and season, `assets/reference/` for original artwork, and `progress.md` for production notes.

## S01E01 — Return on Investment

The approved 60-second animatic is at `output/S01E01-Return-On-Investment.mp4` in the production workspace. To rebuild it from the saved lip-sync cues and approved recordings, run this from the project directory in the existing Linux production environment:

```sh
python3 engine/render_s01e01_final.py
```

Use `--output` to render a second copy while keeping the approved export. The renderer uses NumPy, SoundFile, librsvg's `rsvg-convert`, and FFmpeg. Keep a local backup of `S01E01-animatic-four-gpus-audio.wav` at the project root and the three approved MP3s in `assets/music/` with their original filenames. These audio files are Git-ignored. The renderer verifies the input hashes, and the adjacent music JSON files record the generation settings.

The final MP4 includes selectable English, standard German, and neutral Latin American Spanish subtitles, with English marked as the default. The render command embeds the editable SRT files from `episodes/subtitles/`.
