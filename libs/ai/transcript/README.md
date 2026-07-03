# M2 - Transcript & Metadata Extraction

Whisper large-v3 via faster-whisper (CTranslate2, ~4x faster) + pyannote-audio 3.x
diarization + silero VAD. Produces timestamped transcripts (word + segment level),
detected language, speaker labels, confidence.

**Lead:** Aryan · **Support:** Zubair

See [`libs/ai/transcript/src/ice_transcript/__init__.py`](src/ice_transcript/__init__.py) for the full spec.
