"""
Centralized database query strings for the application.
All queries use PostgreSQL parameter placeholders (%s).
"""

# User queries
QUERY_GET_USER_BY_EMAIL = "SELECT id, password_hash, bgg_id, is_admin FROM users WHERE email = %s AND oauth_provider = 'email'"
QUERY_GET_USER_BY_ID = "SELECT id, email, username, is_admin FROM users WHERE id = %s"
QUERY_GET_USER_BY_OAUTH = "SELECT id, email, username, is_admin FROM users WHERE oauth_provider = %s AND oauth_id = %s"
QUERY_GET_USER_BY_USERNAME = "SELECT id FROM users WHERE username = %s AND id != %s"
QUERY_GET_USER_IS_ADMIN = "SELECT is_admin FROM users WHERE id = %s"
QUERY_UPDATE_USERNAME = "UPDATE users SET username = %s WHERE id = %s"
QUERY_UPDATE_BGG_ID = "UPDATE users SET bgg_id = %s WHERE id = %s"
QUERY_GET_NEXT_USER_ID = "SELECT COALESCE(MAX(id), 0) + 1 FROM users"
QUERY_INSERT_USER_EMAIL = """INSERT INTO users (id, email, username, oauth_provider, password_hash)
                             VALUES (%s, %s, %s, 'email', %s) RETURNING id"""
QUERY_INSERT_USER_OAUTH = """INSERT INTO users (id, email, username, oauth_provider, oauth_id)
                             VALUES (%s, %s, %s, %s, %s) RETURNING id"""

# Collection queries
QUERY_GET_USER_COLLECTION = "SELECT game_id FROM user_collections WHERE user_id = %s"
QUERY_GET_COLLECTION_GAMES = """SELECT uc.game_id, g.name, g.year_published, g.thumbnail, uc.added_at,
                g.average_rating, uc.personal_rating
           FROM user_collections uc
           JOIN games g ON uc.game_id = g.id
           WHERE uc.user_id = %s
           ORDER BY {order_by}"""
QUERY_CHECK_GAME_IN_COLLECTION = "SELECT personal_rating FROM user_collections WHERE user_id = %s AND game_id = %s"
QUERY_ADD_TO_COLLECTION = "INSERT INTO user_collections (user_id, game_id, personal_rating) VALUES (%s, %s, %s)"
QUERY_UPDATE_COLLECTION_RATING = "UPDATE user_collections SET personal_rating = %s WHERE user_id = %s AND game_id = %s"
QUERY_REMOVE_FROM_COLLECTION = "DELETE FROM user_collections WHERE user_id = %s AND game_id = %s"
QUERY_ADD_TO_COLLECTION_SIMPLE = "INSERT INTO user_collections (user_id, game_id) VALUES (%s, %s) ON CONFLICT DO NOTHING"

# Game queries
QUERY_GET_GAME_BY_ID = "SELECT id FROM games WHERE id = %s"
QUERY_GET_GAME_DETAILS = "SELECT id, name, year_published, thumbnail, average_rating, num_ratings, min_players, max_players, description FROM games WHERE id = %s"
QUERY_GET_GAME_NAME = "SELECT name FROM games WHERE id = %s"
QUERY_GET_GAMES_BY_IDS = "SELECT id, name FROM games WHERE id IN ({placeholders})"

# Search queries
QUERY_SEARCH_GAMES_SINGLE_WORD = """SELECT DISTINCT g.id, g.name, g.year_published, g.thumbnail, g.average_rating, g.num_ratings
                     FROM games g
                     LEFT JOIN game_mechanics gm ON gm.game_id = g.id
                     LEFT JOIN mechanics m ON m.id = gm.mechanic_id
                     LEFT JOIN game_categories gc ON gc.game_id = g.id
                     LEFT JOIN categories c ON c.id = gc.category_id
                     LEFT JOIN game_designers gd ON gd.game_id = g.id
                     LEFT JOIN designers d ON d.id = gd.designer_id
                     LEFT JOIN game_publishers gp ON gp.game_id = g.id
                     LEFT JOIN publishers p ON p.id = gp.publisher_id
                     WHERE LOWER(g.name) LIKE LOWER(%s)
                        OR LOWER(m.name) LIKE LOWER(%s)
                        OR LOWER(c.name) LIKE LOWER(%s)
                        OR LOWER(d.name) LIKE LOWER(%s)
                        OR LOWER(p.name) LIKE LOWER(%s)
                     ORDER BY g.num_ratings DESC NULLS LAST, g.average_rating DESC NULLS LAST, g.name
                     LIMIT %s"""

QUERY_SEARCH_MECHANICS = """SELECT DISTINCT id, name FROM mechanics
                   WHERE LOWER(name) LIKE LOWER(%s)
                   ORDER BY name LIMIT %s"""

QUERY_SEARCH_CATEGORIES = """SELECT DISTINCT id, name FROM categories
                   WHERE LOWER(name) LIKE LOWER(%s)
                   ORDER BY name LIMIT %s"""

QUERY_SEARCH_DESIGNERS = """SELECT DISTINCT id, name FROM designers
                   WHERE LOWER(name) LIKE LOWER(%s)
                   ORDER BY name LIMIT %s"""

QUERY_SEARCH_ARTISTS = """SELECT DISTINCT id, name FROM artists
                   WHERE LOWER(name) LIKE LOWER(%s)
                   ORDER BY name LIMIT %s"""

QUERY_SEARCH_PUBLISHERS = """SELECT DISTINCT id, name FROM publishers
                   WHERE LOWER(name) LIKE LOWER(%s)
                   ORDER BY name LIMIT %s"""

# Chat queries
QUERY_GET_CHAT_THREAD = "SELECT id FROM chat_threads WHERE id = %s AND user_id = %s"
QUERY_GET_CHAT_MESSAGES = (
    "SELECT id, role, message, metadata, created_at FROM chat_messages WHERE thread_id = %s ORDER BY created_at ASC"
)
QUERY_INSERT_CHAT_THREAD = "INSERT INTO chat_threads (user_id, title) VALUES (%s, %s) RETURNING id"
QUERY_INSERT_CHAT_MESSAGE = "INSERT INTO chat_messages (thread_id, role, message) VALUES (%s, %s, %s)"
QUERY_INSERT_CHAT_MESSAGE_WITH_METADATA = (
    "INSERT INTO chat_messages (thread_id, role, message, metadata) VALUES (%s, %s, %s, %s)"
)
QUERY_UPDATE_CHAT_THREAD = "UPDATE chat_threads SET updated_at = CURRENT_TIMESTAMP WHERE id = %s"

# Feature queries
QUERY_GET_GAME_DESIGNERS = """SELECT d.name FROM designers d
                               JOIN game_designers gd ON gd.designer_id = d.id
                               WHERE gd.game_id = %s ORDER BY d.name"""

QUERY_GET_GAME_FEATURES_UNION = """SELECT 'mechanics' as type, m.name, '⚙️' as icon
                           FROM mechanics m JOIN game_mechanics gm ON gm.mechanic_id = m.id WHERE gm.game_id = %s
                           UNION ALL
                           SELECT 'categories' as type, c.name, '🏷️' as icon
                           FROM categories c JOIN game_categories gc ON gc.category_id = c.id WHERE gc.game_id = %s
                           UNION ALL
                           SELECT 'designers' as type, d.name, '👤' as icon
                           FROM designers d JOIN game_designers gd ON gd.designer_id = d.id WHERE gd.game_id = %s
                           UNION ALL
                           SELECT 'artists' as type, a.name, '🎨' as icon
                           FROM artists a JOIN game_artists ga ON ga.artist_id = a.id WHERE ga.game_id = %s
                           LIMIT 5"""

# Scoring queries
QUERY_GET_SCORING_MECHANISM = """SELECT id, criteria_json, created_at
                   FROM scoring_mechanisms
                   WHERE game_id = %s AND status = 'approved'
                   ORDER BY created_at DESC LIMIT 1"""

QUERY_CHECK_PENDING_SCORING = """SELECT id FROM scoring_mechanisms WHERE game_id = %s AND status = 'pending'"""
QUERY_INSERT_SCORING_MECHANISM = """INSERT INTO scoring_mechanisms (game_id, criteria_json, status)
                             VALUES (%s, %s, 'pending') RETURNING id"""
QUERY_UPDATE_SCORING_MECHANISM = """UPDATE scoring_mechanisms
                             SET criteria_json = %s, created_at = CURRENT_TIMESTAMP
                             WHERE id = %s"""

# Admin queries
QUERY_GET_ALL_USERS = "SELECT id, email, username, is_admin, created_at FROM users ORDER BY created_at DESC"
QUERY_DELETE_USER = "DELETE FROM users WHERE id = %s"
QUERY_GET_FEATURE_MODS = """SELECT feature_type, feature_id, action
               FROM feature_mods
               WHERE game_id = %s
               ORDER BY created_at DESC"""
QUERY_GET_AVAILABLE_FEATURES = "SELECT id, name FROM {table_name} ORDER BY name"
QUERY_CHECK_FEATURE_MOD = """SELECT id FROM feature_mods
               WHERE game_id = %s AND feature_type = %s AND feature_id = %s AND action = %s"""
QUERY_DELETE_FEATURE_MOD = """DELETE FROM feature_mods
               WHERE game_id = %s AND feature_type = %s AND feature_id = %s AND action = %s"""
QUERY_INSERT_FEATURE_MOD = """INSERT INTO feature_mods (game_id, feature_type, feature_id, action)
               VALUES (%s, %s, %s, %s)"""
QUERY_DELETE_FEATURE_MOD_BY_ID = "DELETE FROM feature_mods WHERE id = %s AND game_id = %s"

# Feedback queries
QUERY_GET_RANDOM_FEEDBACK_QUESTION = """SELECT id, question_text, question_type, is_active
               FROM feedback_questions
               WHERE is_active = %s
               ORDER BY RANDOM()
               LIMIT 1"""
QUERY_GET_FEEDBACK_QUESTION = "SELECT id, question_type FROM feedback_questions WHERE id = %s AND is_active = %s"
QUERY_GET_FEEDBACK_OPTIONS = """SELECT id, option_text FROM feedback_question_options
               WHERE question_id = %s
               ORDER BY display_order, id"""
QUERY_GET_ALL_FEEDBACK_QUESTIONS = """SELECT id, question_text, question_type, is_active, created_at
               FROM feedback_questions
               ORDER BY created_at DESC"""
QUERY_INSERT_FEEDBACK_QUESTION = """INSERT INTO feedback_questions (question_text, question_type, is_active)
               VALUES (%s, %s, %s) RETURNING id"""
QUERY_UPDATE_FEEDBACK_QUESTION = """UPDATE feedback_questions
               SET question_text = %s, question_type = %s, is_active = %s
               WHERE id = %s"""
QUERY_DELETE_FEEDBACK_OPTIONS = "DELETE FROM feedback_question_options WHERE question_id = %s"
QUERY_INSERT_FEEDBACK_OPTION = """INSERT INTO feedback_question_options (question_id, option_text, display_order)
                           VALUES (%s, %s, %s)"""
QUERY_INSERT_FEEDBACK_RESPONSE = """INSERT INTO user_feedback_responses
                   (user_id, question_id, option_id, response, context, thread_id)
                   VALUES (%s, %s, %s, %s, %s, %s) RETURNING id"""

# A/B Test queries
QUERY_GET_AB_TEST_CONFIGS = "SELECT config_key, config_value FROM ab_test_configs WHERE is_active = %s"
QUERY_GET_ALL_AB_TEST_CONFIGS = (
    "SELECT id, config_key, config_value, is_active, created_at, updated_at FROM ab_test_configs ORDER BY created_at DESC"
)
QUERY_INSERT_AB_TEST_CONFIG = """INSERT INTO ab_test_configs (config_key, config_value, is_active)
                   VALUES (%s, %s, %s)"""
QUERY_UPDATE_AB_TEST_CONFIG = """UPDATE ab_test_configs
                   SET config_value = %s, is_active = %s, updated_at = CURRENT_TIMESTAMP
                   WHERE config_key = %s"""
QUERY_DELETE_AB_TEST_CONFIG = "DELETE FROM ab_test_configs WHERE config_key = %s"
QUERY_GET_USER_AB_PREFERENCES = "SELECT config_key, preferred_value FROM user_ab_preferences WHERE user_id = %s"
QUERY_INSERT_USER_AB_PREFERENCE = """INSERT INTO user_ab_preferences (user_id, config_key, preferred_value)
                                       VALUES (%s, %s, %s)
                                       ON CONFLICT (user_id, config_key)
                                       DO UPDATE SET preferred_value = EXCLUDED.preferred_value, updated_at = CURRENT_TIMESTAMP"""
QUERY_DELETE_USER_AB_PREFERENCES = "DELETE FROM user_ab_preferences WHERE user_id = %s"

# Marketplace queries (placeholder for future implementation)
QUERY_GET_MARKETPLACE_ENTRIES = "SELECT id, game_id, marketplace_name, url, price, currency, shipping_cost, country FROM marketplace_entries WHERE game_id = %s"
