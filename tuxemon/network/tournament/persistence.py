from pathlib import Path
from typing import Optional

from tuxemon.network.tournament.models import Tournament


def save_tournament(tournament: Tournament, filepath: Path) -> None:
    """Serializes a tournament to JSON and saves it."""
    # Convert Pydantic model to dict, then to JSON
    # Pydantic v2 uses model_dump_json()
    data = tournament.model_dump_json(indent=2)
    filepath.write_text(data, encoding="utf-8")


def load_tournament(filepath: Path) -> Optional[Tournament]:
    """Loads a tournament from a JSON file."""
    if not filepath.exists():
        return None
    data = filepath.read_text(encoding="utf-8")
    return Tournament.model_validate_json(data)
