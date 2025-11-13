# Animechan API Project

This mini project demonstrates how to use the Animechan API for a course assignment. It includes:

- `client.py`: API client with caching, retries (exponential backoff), and rate-limit sleep
- `collect_data.py`: Collect quotes from Animechan or use bundled offline samples
- `analyze_quotes.py`: Simple statistics over collected quotes
- `data/sample_quotes.json`: Offline sample data

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install requests

# Collect sample data (offline)
python -m api_use.animechan_project.collect_data --output outputs/sample.json --offline

# Analyze data
python -m api_use.animechan_project.analyze_quotes outputs/sample.json --export outputs/summary.json
```

For live collection, remove `--offline` and specify characters or anime titles explicitly.

## Project Layout

```
animechan_project/
├── __init__.py
├── README.md
├── analyze_quotes.py
├── client.py
├── collect_data.py
└── data/
    └── sample_quotes.json
```

## Testing Tips

Use `pytest` with `requests-mock` (or `responses`) to unit-test caching, retry, and error handling in the client.


