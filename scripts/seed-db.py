#!/usr/bin/env python3
"""Apply migrations + seed sample data. `make seed` runs this."""
from __future__ import annotations

import runpy

runpy.run_path("db/seed/seed.py", run_name="__main__")
