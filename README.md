# PRÓLOGOS — Test Deploy (Streamlit)

This repository contains a Streamlit app (`app.py`) and a small FastAPI service (`main.py`) for jurimetry analysis. The following files were added/updated to prepare for a Streamlit test deploy:

- `requirements.txt` — pinned runtime dependencies
- `.gitignore` — extended to ignore envs, caches and DB files
- `Procfile` — a simple command usable by Heroku-like services (runs Streamlit)
- `.streamlit/config.toml` — basic Streamlit server settings
- `.env.example` — example environment variables to copy to `.env`

Quick local run

1. Create virtualenv and install deps:

   python -m venv .venv
   .venv\Scripts\activate (Windows) or source .venv/bin/activate (Unix)
   pip install -r requirements.txt

2. Add your Groq API key to `.env` (copy `.env.example`):

   GROQ_API_KEY=your_groq_api_key_here

3. Run the Streamlit app:

   streamlit run app.py

Deploy to Streamlit Community Cloud

1. Push repo to GitHub.
2. Go to https://share.streamlit.io and connect repo/branch.
3. Set the secret `GROQ_API_KEY` in the app settings (so you don't store it in Git).
4. Deploy.

Notes & Caveats

- `sentence-transformers` requires `torch`. The pinned versions in `requirements.txt` are chosen as reasonable defaults for testing, but you may want to adapt them to your target environment.
- Keep your `.env` and any secrets out of source control.
- If you plan to deploy multiple processes (API + Streamlit), consider using a container or separate apps.
