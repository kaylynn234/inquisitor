from typing import Any


__all__ = ("GameError", "GameNotFound", "StatusParseError")


class GameError(Exception):
    """Base exception type for game-specific exceptions."""

    game_name: str

    def __init__(self, *args: Any, game_name: str) -> None:
        super().__init__(*args)
        self.game_name = game_name


class GameNotFound(GameError):
    """The specified game was not found."""

    def __init__(self, game_name: str) -> None:
        super().__init__(
            f"couldn't find a game named {game_name}; note that game names are case-sensitive",
            game_name=game_name,
        )


class StatusParseError(GameError):
    """The game status page could not be parsed."""

    def __init__(self, game_name: str) -> None:
        super().__init__(f"unable to parse status page for {game_name}", game_name=game_name)
