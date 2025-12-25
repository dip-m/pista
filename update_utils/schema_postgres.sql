-- PostgreSQL schema for Pista
-- Converted from SQLite schema with OAuth support

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

-- Updated users table with OAuth support
CREATE TABLE IF NOT EXISTS users (
    id             INTEGER PRIMARY KEY,  -- Using INTEGER to match SQLite migration
    email          TEXT UNIQUE,
    username       TEXT,
    oauth_provider TEXT,  -- 'google', 'microsoft', 'meta', 'email'
    oauth_id       TEXT,  -- OAuth provider user ID
    password_hash  TEXT,  -- Only for email-based auth
    bgg_id         TEXT,
    is_admin       BOOLEAN DEFAULT FALSE,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_oauth UNIQUE(oauth_provider, oauth_id)
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_oauth ON users(oauth_provider, oauth_id);

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
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    title       TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id          SERIAL PRIMARY KEY,
    thread_id   INTEGER NOT NULL,
    role        TEXT NOT NULL,
    message     TEXT NOT NULL,
    metadata    TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (thread_id) REFERENCES chat_threads(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS feature_mods (
    id          SERIAL PRIMARY KEY,
    game_id     INTEGER NOT NULL,
    feature_type TEXT NOT NULL,
    feature_id  INTEGER NOT NULL,
    action      TEXT NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS feedback_questions (
    id          SERIAL PRIMARY KEY,
    question_text TEXT NOT NULL,
    question_type TEXT NOT NULL,
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feedback_question_options (
    id          SERIAL PRIMARY KEY,
    question_id INTEGER NOT NULL,
    option_text TEXT NOT NULL,
    display_order INTEGER DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (question_id) REFERENCES feedback_questions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_feedback_responses (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    question_id INTEGER,
    option_id   INTEGER,
    response    TEXT,
    context     TEXT,
    thread_id   INTEGER,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES feedback_questions(id) ON DELETE SET NULL,
    FOREIGN KEY (option_id) REFERENCES feedback_question_options(id) ON DELETE SET NULL,
    FOREIGN KEY (thread_id) REFERENCES chat_threads(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS ab_test_configs (
    id          SERIAL PRIMARY KEY,
    config_key  TEXT NOT NULL UNIQUE,
    config_value TEXT NOT NULL,
    is_active   BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_ab_preferences (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    config_key  TEXT NOT NULL,
    preferred_value TEXT NOT NULL,  -- 'A' or 'B' or config value
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, config_key)
);

CREATE TABLE IF NOT EXISTS fake_door_interactions (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER,
    interaction_type TEXT NOT NULL,  -- 'image_upload' or 'rules_explainer'
    context     TEXT,  -- JSON string with context (game_id, message, etc.)
    metadata    TEXT,  -- Additional metadata (file info, etc.)
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS scoring_mechanisms (
    id              SERIAL PRIMARY KEY,
    game_id         INTEGER NOT NULL,
    criteria_json   TEXT NOT NULL,  -- JSON structure with scoring criteria
    status          TEXT NOT NULL DEFAULT 'pending',  -- 'pending', 'approved', 'rejected'
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at     TIMESTAMP,
    reviewed_by     INTEGER,  -- Admin user ID who reviewed
    review_notes    TEXT,
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
    FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE(game_id, status)  -- Only one approved mechanism per game
);

CREATE TABLE IF NOT EXISTS user_scoring_sessions (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER NOT NULL,
    game_id             INTEGER NOT NULL,
    mechanism_id        INTEGER NOT NULL,
    intermediate_scores_json TEXT,  -- JSON array of intermediate scores
    final_score         REAL,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
    FOREIGN KEY (mechanism_id) REFERENCES scoring_mechanisms(id) ON DELETE CASCADE
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_game_mechanics_game ON game_mechanics(game_id);
CREATE INDEX IF NOT EXISTS idx_game_categories_game ON game_categories(game_id);
CREATE INDEX IF NOT EXISTS idx_user_collections_user ON user_collections(user_id);

