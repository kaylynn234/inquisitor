import attrs
import cattrs
import toml


@attrs.define()
class BotConfig:
    token: str
    refresh_frequency: int = 15


@attrs.define()
class DatabaseConfig:
    host: str
    port: int
    user: str | None = None
    password: str | None = None
    database: str | None = None


@attrs.define()
class Config:
    bot: BotConfig
    database: DatabaseConfig

    @classmethod
    def load(cls) -> "Config":
        """Read configuration from the current working directory."""

        return cattrs.structure(toml.load("config.toml"), Config)
