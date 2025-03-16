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
