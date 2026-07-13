#!/usr/bin/env python3
"""Seed the dev database. `make seed` runs this.

Redirects to the ORM-compatible seed (scripts/seed_dev.py) which creates a
tenant, a verified user (dev@ice.dev / devpass123), and is idempotent against
the Integer-PK ORM schema used by create_all.
"""
from __future__ import annotations

import os
import runpy

_HERE = os.path.dirname(os.path.abspath(__file__))
runpy.run_path(os.path.join(_HERE, "seed_dev.py"), run_name="__main__")
