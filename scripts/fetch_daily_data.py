#!/usr/bin/env python3
"""CLI entry point for daily data fetch."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.pipeline import run_pipeline

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-llm", action="store_true")
    args = parser.parse_args()

    result = run_pipeline(skip_llm=args.skip_llm)
    sys.exit(0 if result["status"] != "failed" else 1)
