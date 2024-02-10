CREATE SCHEMA IF NOT EXISTS inquisitor;

CREATE TABLE IF NOT EXISTS inquisitor.tracked_games (
    game_name TEXT PRIMARY KEY,
    current_turn INT NOT NULL DEFAULT 0,
    guild_id BIGINT NOT NULL,
    announcement_channel BIGINT NOT NULL,
    announcement_role BIGINT
);
