# Documentation

This folder contains all project documentation files (`.md` files).

## Organization

All markdown documentation files for the Pista project are stored in this `docs/` folder to keep the project root clean and organized.

**Note:** The main `README.md` file remains in the project root for quick reference. Frontend-specific README files (e.g., `frontend/README.md`, `frontend/CHANGELOG.md`) remain in their respective directories for package management tools.

## File Naming

- Files moved from the root directory keep their original names
- Files moved from subdirectories are prefixed with their source directory (e.g., `FRONTEND_DEPLOYMENT.md` for `frontend/DEPLOYMENT.md`)

## Adding New Documentation

**All new markdown documentation files should be placed in this `docs/` folder** to maintain consistency and keep the project structure clean.

Exceptions:
- `README.md` in the project root (main project README)
- `README.md` and `CHANGELOG.md` in `frontend/` (for npm/package management)

## Documentation Files

This folder contains 34+ documentation files covering:
- Deployment guides (Railway, Render, Netlify, etc.)
- Testing documentation
- Database migration guides (PostgreSQL, SQLite, OAuth)
- Environment setup instructions
- Implementation summaries
- And more...
