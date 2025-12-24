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
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    email          TEXT UNIQUE,
    username       TEXT,
    oauth_provider TEXT,  -- 'google', 'microsoft', 'meta', 'email'
    oauth_id       TEXT,  -- OAuth provider user ID
    password_hash  TEXT,  -- Only for email-based auth
    bgg_id         TEXT,
    is_admin       INTEGER DEFAULT 0,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create unique constraint on (oauth_provider, oauth_id) for SQLite
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_oauth_unique ON users(oauth_provider, oauth_id) WHERE oauth_provider IS NOT NULL AND oauth_id IS NOT NULL;

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

CREATE TABLE IF NOT EXISTS feature_mods (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id     INTEGER NOT NULL,
    feature_type TEXT NOT NULL,  -- 'mechanic', 'category', 'designer', 'artist', 'publisher', 'family'
    feature_id  INTEGER NOT NULL,
    action      TEXT NOT NULL,  -- 'add' or 'remove'
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS feedback_questions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    question_text TEXT NOT NULL,
    question_type TEXT NOT NULL,  -- 'rating', 'multiple_choice', 'text', 'like_dislike'
    is_active   INTEGER DEFAULT 1,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feedback_question_options (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL,
    option_text TEXT NOT NULL,
    display_order INTEGER DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (question_id) REFERENCES feedback_questions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_feedback_responses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    question_id INTEGER,
    option_id   INTEGER,  -- Reference to feedback_question_options.id for multiple choice questions
    response    TEXT,  -- Text response for text/rating questions, or like/dislike
    context     TEXT,  -- Additional context about the feedback (e.g., message_id, thread context)
    thread_id   INTEGER,  -- Link to chat thread if applicable
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES feedback_questions(id) ON DELETE SET NULL,
    FOREIGN KEY (option_id) REFERENCES feedback_question_options(id) ON DELETE SET NULL,
    FOREIGN KEY (thread_id) REFERENCES chat_threads(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS ab_test_configs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key  TEXT NOT NULL UNIQUE,  -- e.g., 'use_rarity_weighting', 'feature_exclusion_enabled'
    config_value TEXT NOT NULL,  -- JSON string with config details
    is_active   INTEGER DEFAULT 0,  -- Whether A/B testing is enabled for this config
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);