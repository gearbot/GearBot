CREATE TABLE IF NOT EXISTS config
(
    guild_id bigint NOT NULL,
    config json NOT NULL,
    PRIMARY KEY (guild_id)
);
