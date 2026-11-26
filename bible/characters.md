# Cast and style
Walter: veteran engineer, sarcastic, technically competent, gray hair, blue sweater, dry mature voice. Kyle: enthusiastic overconfident founder, spiky brown hair, green hoodie, energetic young voice. Susan: pragmatic accountant, dark bob, purple outfit with white collar, calm deadpan voice. Chip: confidently wrong AI intern, synthetic voice; robot prop concept exists but physical embodiment is not finalized. Use flat shapes, bold outlines, simple cutout motion and original designs. Preserve the selected rig concept 3 and use subsequent color reference as palette guidance. Running gags: loud fans, Kyle's whiteboard, Susan's calculator, Walter's “It worked yesterday” mug, Chip status light, successful cat account, unseen investor and Walter's closing stare. See season JSON for episode outlines.

## Walter’s approved voice

Use Kokoro `am_michael` with standard pronunciation, a measured keynote cadence, and a quieter follow-up. The approved reference is `walter-keynote-audition.wav`. For the pilot line, synthesize the statement at 0.90× and the question at 0.94×, trim model padding, and leave a 650 ms beat before the question. Set the question to 86% of the statement’s gain, then apply a 2 dB cut at 3.4 kHz (Q 1) and 90% overall gain.

## Susan’s approved voice

Use Marlo for Susan’s calm Australian-English deadpan. The approved audition uses Piper 1.8.0, speaker ID 2, and length scale 1.08. The voice model is CC BY 4.0. [Data Craftsman’s Australian English voice model](https://huggingface.co/DataCraftsmanAustralia/piper-en_AU-librivox-medium)
