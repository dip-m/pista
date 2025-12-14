PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS games (
    id              INTEGER PRIMARY KEY,  -- BGG id
    name            TEXT NOT NULL,
    description     TEXT,
    year_published  INTEGER,
    min_players     INTEGER,
    max_players     INTEGER,
    playing_time    INTEGER,
    min_playtime    INTEGER,
    max_playtime    INTEGER,
    min_age         INTEGER,
    thumbnail       TEXT,
    image           TEXT,
    average_rating  REAL,
    bayes_rating    REAL,
    avg_weight      REAL,
    num_ratings     INTEGER,
    num_comments    INTEGER,
    ranks_json      TEXT,
    polls_json      TEXT
);

CREATE TABLE IF NOT EXISTS mechanics (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS families (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS designers (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS artists (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS publishers (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS game_mechanics (
    game_id     INTEGER NOT NULL,
    mechanic_id INTEGER NOT NULL,
    PRIMARY KEY (game_id, mechanic_id),
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
    FOREIGN KEY (mechanic_id) REFERENCES mechanics(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS game_categories (
    game_id     INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    PRIMARY KEY (game_id, category_id),
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS game_families (
    game_id     INTEGER NOT NULL,
    family_id   INTEGER NOT NULL,
    PRIMARY KEY (game_id, family_id),
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
    FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS game_designers (
    game_id     INTEGER NOT NULL,
    designer_id INTEGER NOT NULL,
    PRIMARY KEY (game_id, designer_id),
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
    FOREIGN KEY (designer_id) REFERENCES designers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS game_artists (
    game_id     INTEGER NOT NULL,
    artist_id   INTEGER NOT NULL,
    PRIMARY KEY (game_id, artist_id),
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
    FOREIGN KEY (artist_id) REFERENCES artists(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS game_publishers (
    game_id      INTEGER NOT NULL,
    publisher_id INTEGER NOT NULL,
    PRIMARY KEY (game_id, publisher_id),
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
    FOREIGN KEY (publisher_id) REFERENCES publishers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS game_profiles (
    game_id      INTEGER PRIMARY KEY,
    profile_text TEXT NOT NULL,
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS game_embeddings (
    game_id     INTEGER PRIMARY KEY,
    vector_json TEXT NOT NULL,
    dim         INTEGER NOT NULL,
    model_name  TEXT NOT NULL,
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    bgg_id      TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_collections (
    user_id         INTEGER NOT NULL,
    game_id         INTEGER NOT NULL,
    added_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    personal_rating REAL,
    PRIMARY KEY (user_id, game_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS chat_threads (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    title       TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id   INTEGER NOT NULL,
    role        TEXT NOT NULL,  -- 'user' or 'assistant'
    message     TEXT NOT NULL,
    metadata    TEXT,  -- JSON string for results, query_spec, etc.
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (thread_id) REFERENCES chat_threads(id) ON DELETE CASCADE
);