import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def _temp_gemini_cache(monkeypatch, tmp_path):
    """Tests never read or write the committed results/gemini_cache.json."""
    import copilot

    monkeypatch.setattr(copilot, "CACHE_FILE", tmp_path / "gemini_cache.json")
    monkeypatch.setattr(copilot, "_skip_until", {})
