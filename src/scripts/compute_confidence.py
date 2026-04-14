#!/usr/bin/env python3
"""
compute_confidence.py — CLI wrapper for MC confidence propagation.

Usage:
    python scripts/compute_confidence.py --seed 42
    python scripts/compute_confidence.py --sensitivity
    python scripts/compute_confidence.py --seed 42 --samples 5000

Called by .github/workflows/weekly.yml every Monday.
"""

import sys
from pathlib import Path

# Ensure extraction/ is importable
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "extraction"))

from extraction.mc_engine import main

if __name__ == "__main__":
    main()
