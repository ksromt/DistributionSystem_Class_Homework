"""
Basic analysis over Animechan quote dataset.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Sequence


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze collected Animechan quotes.")
    parser.add_argument("input", type=Path, help="Input JSON file produced by collect_data.py")
    parser.add_argument(
        "--export",
        type=Path,
        help="Optional path to save analysis summary as JSON",
    )
    return parser.parse_args(argv)


def analyze(data: Dict[str, Any]) -> Dict[str, Any]:
    quotes = data.get("data", [])
    anime_counter = Counter()
    character_counter = Counter()
    for item in quotes:
        anime_counter[item.get("anime", "Unknown")] += 1
        character_counter[item.get("character", "Unknown")] += 1

    return {
        "records": len(quotes),
        "anime_top": anime_counter.most_common(),
        "character_top": character_counter.most_common(),
    }


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    with args.input.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    summary = analyze(payload)

    print(f"Total quotes: {summary['records']}")
    print("Top anime:")
    for anime, count in summary["anime_top"]:
        print(f"  {anime}: {count}")

    print("Top characters:")
    for character, count in summary["character_top"]:
        print(f"  {character}: {count}")

    if args.export:
        args.export.parent.mkdir(parents=True, exist_ok=True)
        with args.export.open("w", encoding="utf-8") as fh:
            json.dump(summary, fh, ensure_ascii=False, indent=2)
        print(f"Summary exported to {args.export}")


if __name__ == "__main__":
    main()


