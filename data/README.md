# Sample data + fixtures

- `samples/` — short sample tutorial clips + transcripts (for Phase-0 smoke tests). Large media is gitignored; commit only small clips + `.md` descriptors.
- `fixtures/` — canned JSON (transcript, visual items, curriculum) used by unit tests so they don't need live services.
- `raw/` and `processed/` are gitignored — large dataset downloads go there (see `scripts/download-dataset.py`).
