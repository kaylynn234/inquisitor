# Inquisitor

Inquisitor is a small Discord bot for tracking turns in Dominion 6. That's it! It periodically scrapes the status pages
generated by the Dominion 6 server to determine when a new turn can be played, and announces it in a configured channel.
Multiple games can be tracked at once, and you can configure them to mention certain roles so that people get notified.

The bot requires the message intent configured in your Discord Developer Portal for things to function properly. Slash
commands aren't supported.

You can either use the bot's @mention as a command prefix, or `in!`. `in!help` will display some basic help on all of
the commands supported by the bot. `in!help <command>` will display more detailed help on a specific command. Note that
in all of these examples, you can replace the `in!` prefix with a bot @mention.

## Running it: the normal way

You'll need [Poetry](https://python-poetry.org/) and a Postgres database. It's fairly simple from there:

1. Clone this repository and `cd` into it using your terminal. That part should go without saying!
2. Copy `config.example.toml` from this directory, rename it to `config.toml`, and edit as necessary. You'll need to
   make sure to set up a Discord bot account, so that you can enter a token here. You'll also need to fill in the
   database sections as relevant for your database setup.
3. Run `poetry run python launch.py`. You may need to use `python3` or similar here, instead of `python`, depending on
   your environment.

## Running it: the Docker Compose way

This is slightly more involved, but has the benefit of dealing with running a Postgres server for you.

1. This is the same as last time. Clone this repository, and `cd` into it using your terminal.
2. Set the `POSTGRES_PASSWORD` environment variable. This password will be used for the configured Postgres server.
3. Copy `config.example.toml` and rename it to `config.toml`. Again, this is like last time, but there are a few things
   you'll still need to keep in mind:

   - The database host must be set to `postgres`.
   - The database user must be set to `inquisitor`.
   - The database password must be set to the same password you used in step 2.

   And don't forget your bot token, either!
4. Run `docker volume create inquisitor-postgres-data` to create a volume for the Postgres data to be stored in.
5. Run `docker compose up` to start the thing! You may want to use the ``--exit-code-from bot` option, or to use the
   `--detach` flag to start both services without clogging up your terminal too much.

That's about it!