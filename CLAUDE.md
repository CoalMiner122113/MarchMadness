# CLAUDE.md

## Project Overview

NCAA March Madness tournament bracket simulator built with Streamlit. Uses KenPom stats and ESPN APIs to predict tournament outcomes. Target year: 2026.

**Stack:** Python + Streamlit frontend, MySQL database backend, Selenium for KenPom scraping, ESPN REST APIs.

## Commands

```bash
# Run the app
streamlit run app.py --server.address 0.0.0.0

# Run all tests (mocked/fast only)
pytest

# Run live external service tests (ESPN/KenPom calls)
pytest -m live

# Run a single test file
pytest tests/test_app_frontend.py

# Lint
ruff check .
```

## Environment Setup

Requires a `.env` file (not committed):
```
MYSQL_HOST = 'localhost'
MYSQL_USER = 'root'
MYSQL_PASS = 'password'
CHROMEDRIVER_PATH = 'C:/MarchMadness/chromedriver145.exe'
```

Requires a local MySQL instance with a database named `marchMadness`. Tables are auto-created by `sql/sqlHandler.py`.

## Architecture

### Data Flow
1. **Scraping** (`scraping/`) → populates MySQL via `sql/sqlHandler.py`
   - `kpScraper.py`: Selenium-based KenPom scraper (AdjEM, Luck, SOS stats)
   - `espnConnect.py`: ESPN REST API client — team metadata, matchup probabilities, predictor data, moneyline odds
2. **Session state** persisted to `session_data/<uuid>.json` per browser session
3. **Simulation** (`app_logic/`) drives bracket prediction
4. **UI** (`app.py`) is a single-file Streamlit app (~1,274 lines) with 5 main views

### Simulation Logic (`app_logic/`)
- `objDef.py` — `Team` class; `versus()` computes win probability from AdjEM, SOS, and Luck
- `Madness.py` — Bracket structure (R64 → Championship)
- `TournamentLayout.py` — Per-game simulation for each round

**Probability formula (app.py):**
```python
strength = AdjEM + 0.35*sqrt(SOS) + 2.0*luck
prob = 1 / (1 + exp(-(strength_diff / 6)))  # logistic
```

### Database Schema (5 tables)
| Table | Purpose |
|---|---|
| `MBBTeams` | Team metadata — KenPomName, EspnName, NcaaName, IDs |
| `TeamStatsByYear` | AdjEM, Luck, SOS per year |
| `SeedByYear` | Seeds by division and year |
| `TournamentGames` | Per-game results |
| `TournamentResults` | Round reached per team per year |

## Verification (CRITICAL)

Before every commit:
1. Run `pytest` — **all tests must pass**
2. If a test fails, fix it before moving on. Do not skip or delete failing tests.
3. If you add new functionality, add corresponding tests.
4. If you modify existing functionality, verify existing tests still pass and update them if behavior changed.

## Code Style

- Python 3.10+ — use type hints on all function signatures
- Use f-strings, not `.format()` or `%`
- Docstrings on public functions (Google style)
- Keep functions under 50 lines; extract helpers when complexity grows
- Imports: stdlib → third-party → local, separated by blank lines

## Streamlit Guidelines

- Keep business logic out of Streamlit rendering code — call backend functions, don't compute inline
- Use `st.cache_data` or `st.cache_resource` for expensive operations (DB queries, API calls)
- `app.py` is already large (~1,274 lines) — when adding features, extract to modules in `app_logic/` rather than growing `app.py`

## Database Rules

- Use parameterized queries — **never** use f-strings or string concatenation for SQL
- All schema changes require a migration or update to `sql/sqlHandler.py` auto-creation logic
- Close connections/cursors properly (prefer context managers)
- Do not hard-code credentials — they come from `.env`

## External APIs

### ESPN
- These are **undocumented, reverse-engineered endpoints** — they can break without notice
- ESPN predictor data comes from a TeamRankings iframe parsed via HTML
- Moneyline odds fetched from scoreboard API — known to be slow (see recent commits)
- Wrap all ESPN calls in try/except with meaningful error messages
- Cache responses aggressively to avoid rate limiting
- If an endpoint returns unexpected data, fail gracefully with a logged warning — don't crash

### KenPom
- Selenium-based scraper in `scraping/kpScraper.py`; requires ChromeDriver v145
- Respect rate limits and add delays between requests
- Cache KenPom data in MySQL to minimize scrape frequency

## Test Markers

- Default `pytest` runs mocked/fast tests only
- `pytest -m live` opts into tests that hit real external services (ESPN, KenPom)
- When writing new tests, default to mocked. Only use `@pytest.mark.live` for integration tests.

## Git Workflow

- Work on feature branches, not main
- Conventional commit messages: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`
- One logical change per commit
- Run `pytest` before every commit — do not commit with failing tests

## Off-Limits

- Do not modify `.env` or any secrets/config files
- Do not modify database migration history (only add new migrations)
- Do not change ChromeDriver binaries or paths
- Do not install new dependencies without stating why

## When Stuck (Ralph Loop Guidance)

If a task isn't converging after several iterations:
1. Document what's blocking in a `BLOCKED.md` at project root
2. List what was attempted and why it failed
3. Suggest 2-3 alternative approaches
4. Move on to the next task if one is available
