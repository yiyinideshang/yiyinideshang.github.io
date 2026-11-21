#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wrapper around tools/family_spacing.py for the ct4-vocab-sync skill."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools"))
from family_spacing import main  # noqa: E402

if __name__ == "__main__":
    main()
