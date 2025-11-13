import sys
from pathlib import Path

import pytest
import requests
import requests_mock

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api_use.animechan_project.client import AnimechanClient, AnimechanError


def test_cache_hit(monkeypatch):
    with requests_mock.Mocker() as mocker:
        mocker.get(
            "https://api.animechan.io/v1/quotes/random",
            json={"anime": "Naruto", "character": "Naruto Uzumaki", "quote": "..."},
        )
        client = AnimechanClient(cache_ttl=60)
        first = client.get_random_quote()
        second = client.get_random_quote()
        assert first == second
        assert mocker.call_count == 1


def test_retry_and_failure(monkeypatch):
    with requests_mock.Mocker() as mocker:
        mocker.get(
            "https://api.animechan.io/v1/quotes/random",
            status_code=500,
        )
        client = AnimechanClient(max_retries=2, backoff_factor=0)
        with pytest.raises(AnimechanError):
            client.get_random_quote()
        assert mocker.call_count == 3

