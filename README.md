# autojob-bot

Autonomous job application assistant that aggregates listings, tailors documents, and manages outreach.

## Quickstart

1. Copy environment defaults: `cp .env.example .env`
2. Start the stack: `docker compose up -d`
3. Apply migrations: `make migrate`
4. Seed defaults: `python -m app.db.seed`
5. Launch the API: `uvicorn app.api.main:app --reload`

## Features

- Multi-source job ingestion from Greenhouse, Lever, Workday, and RSS feeds
- Automated document tailoring with resume and cover letter templates
- Vector-based job matching with keyword and score filters
- Task queue with scheduled workers for continuous operations
- Notifications via email and Telegram

> **Note:** The project intentionally avoids committing binary assets. Tailored resume and cover letter exports are Markdown/text only today; when ready to add PDF or DOCX generation, extend `app/docs/exports.py` with libraries such as WeasyPrint or python-docx while keeping the repository history text-based.
