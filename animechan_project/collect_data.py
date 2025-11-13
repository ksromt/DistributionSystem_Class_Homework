"""
Animechan API data collection script.

Example:
    python collect_data.py --characters "Lelouch Lamperouge" "Naruto Uzumaki" --shows "One Piece" --output data.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, List, Sequence

from .client import AnimechanClient, AnimechanError, bulk_fetch_quotes

DEFAULT_SAMPLE_FILE = Path(__file__).with_name("data") / "sample_quotes.json"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect quotes from Animechan API.")
    parser.add_argument("--characters", nargs="*", help="Characters to query")
    parser.add_argument("--shows", nargs="*", help="Anime titles to query")
    parser.add_argument("--limit", type=int, default=10, help="Limit per API call (if supported)")
    parser.add_argument("--output", type=Path, required=True, help="Path to write collected JSON data")
    parser.add_argument("--offline", action="store_true", help="Use bundled sample data instead of live API")
    parser.add_argument(
        "--sample",
        type=Path,
        default=DEFAULT_SAMPLE_FILE,
        help="Path to sample data (used when --offline)",
    )
    return parser.parse_args(argv)


def load_sample_quotes(sample_path: Path) -> List[dict]:
    if not sample_path.exists():
        raise FileNotFoundError(f"Sample data not found: {sample_path}")
    with sample_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def collect_live_data(
    characters: Iterable[str] | None,
    shows: Iterable[str] | None,
    *,
    limit: int | None,
) -> List[dict]:
    client = AnimechanClient()
    quotes = bulk_fetch_quotes(client, characters=characters, shows=shows, per_request_limit=limit)
    unique = {(item["anime"], item["character"], item["quote"]): item for item in quotes}
    return list(unique.values())


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    if args.offline:
        quotes = load_sample_quotes(args.sample)
    else:
        try:
            quotes = collect_live_data(args.characters, args.shows, limit=args.limit)
        except AnimechanError as exc:
            print(f"API fetch failed ({exc}), falling back to sample data.")
            quotes = load_sample_quotes(args.sample)

    payload = {
        "meta": {
            "characters": args.characters,
            "shows": args.shows,
            "record_count": len(quotes),
        },
        "data": quotes,
    }
    with args.output.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    print(f"Written {len(quotes)} quotes to {args.output}")


if __name__ == "__main__":
    main()


