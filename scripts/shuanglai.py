#!/usr/bin/env python3
"""Repository-local launcher for the unified CLI."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shuanglai_corpus.cli import main

raise SystemExit(main())
