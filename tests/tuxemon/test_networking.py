from unittest.mock import MagicMock

from tuxemon.db import Direction
from tuxemon.network.networking import CharData, EventData, update_client


class DummySprite:
    def __init__(self) -> None:
        self.tile_pos = (1, 1)
        self.position = [1.0, 1.0]
        self.running = False
        self.facing = Direction.DOWN
        self.set_position_calls = 0

    def set_position(self, pos: tuple[float, float]) -> None:
        self.position = [pos[0], pos[1]]
        self.tile_pos = (int(pos[0]), int(pos[1]))
        self.set_position_calls += 1

    def set_facing(self, direction: Direction) -> None:
        self.facing = direction


def test_char_data_from_dict_accepts_partial_payload() -> None:
    char_data = CharData.from_dict({"facing": "left"})

    assert char_data.tile_pos == (0, 0)
    assert char_data.name == ""
    assert char_data.facing == Direction.LEFT
    assert char_data.running is False


def test_event_data_roundtrip_preserves_direction_and_partial_char() -> None:
    parsed = EventData.from_dict(
        {
            "type": "CLIENT_MAP_UPDATE",
            "event_number": "12",
            "direction": "right",
            "char_dict": {"tile_pos": [2, 3], "facing": "up"},
        }
    )

    encoded = parsed.to_dict()
    assert parsed.event_number == 12
    assert parsed.direction == "right"
    assert encoded["direction"] == "right"
    assert encoded["char_dict"]["tile_pos"] == (2, 3)
    assert encoded["char_dict"]["facing"] == "UP"


def test_event_data_from_dict_defaults_event_number_for_ping() -> None:
    parsed = EventData.from_dict({"type": "PING"})
    assert parsed.event_number == 0


def test_update_client_only_moves_when_tile_is_out_of_sync() -> None:
    sprite = DummySprite()
    game = MagicMock()

    update_client(
        sprite,
        CharData(
            tile_pos=(1, 1),
            name="Remote",
            facing=Direction.LEFT,
            running=True,
        ),
        game,
    )
    assert sprite.set_position_calls == 0
    assert sprite.facing == Direction.LEFT
    assert sprite.running is True

    update_client(
        sprite,
        CharData(
            tile_pos=(4, 2),
            name="Remote",
            facing=Direction.RIGHT,
            running=False,
        ),
        game,
    )
    assert sprite.set_position_calls == 1
    assert sprite.tile_pos == (4, 2)
    assert sprite.position == [4.0, 2.0]
