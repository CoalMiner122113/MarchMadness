# MarchMadness
Auto create brackets based on KenPom stats.

## Project structure
- `app.py` - Streamlit entrypoint
- `app_logic/` - simulation and team model logic
- `scraping/` - KenPom scraping logic
- `sql/` - MySQL setup/import/export logic
- `tests/` - test and experimentation scripts

## Setup (Linux example)
source ./venv/bin/activate
pip install -r requirements.txt

## Run app
streamlit run app.py --server.address 0.0.0.0

Suggested Solutions

  Option A — Cache ESPN calls with @st.cache_data (low effort, biggest immediate gain)

  Decorate _load_espn_probabilities and _load_scoreboard_matchups with @st.cache_data(ttl=300). This eliminates the

  repeated scoreboard hits on every rerender. The duplicate fetch_matchup_probabilities /

  fetch_raw_tournament_matchups functions can also be collapsed into one and cached, eliminating the redundant

  double-hit entirely.

  Option B — Persist predictor bootstrap state in session JSON (medium effort, directly fixes option 3)

  After the first successful fetch_predictor_bootstrap, save the result into payload["espn_predictor_state"] and

  call save_session_payload. On subsequent calls, check if that key exists before hitting the network. This

  eliminates 2 HTTP GETs per "Update ESPN Probabilities" click and makes bootstrap retrieval nearly instant after

  the first call.

  Option C — Pre-fetch and store predictor probabilities per round rather than replaying picks (high effort, fixes

  option 2)

  Instead of replaying the bracket state via makePick.php on demand, fetch predictor probabilities for all 6 rounds

  at once during a single bootstrap/load pass and store them in the session JSON (keyed by round name). On "Update

  ESPN Probabilities", only re-fetch the single target round. This caps the network cost at a fixed number of

  requests regardless of how deep into the tournament you are, and eliminates the O(N) pick-replay chain entirely.