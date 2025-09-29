# 3MTT Learner Email Reminder

A Python automation package that retrieves learner data from the **Darey API**, filters inactive or low-performing learners, and sends personalized reminder emails using **AWS SES**.

The workflow is designed to run **weekly via GitHub Actions**, ensuring learners receive timely nudges to keep learning momentum while the process remains **scalable, resilient, and fully automated**.

---

## 📌 Features

* **Darey API Downloader** – asynchronously fetches learners in batches with retries.
* **Learner Filtering** – detects inactive learners and low-performing learners using configurable thresholds.
* **Email Delivery** – sends reminders via AWS SES with styled HTML templates.
* **Data Analysis** – includes a Jupyter notebook (`analysis.ipynb`) and visualizations (`assets/`) for insights.
* **Retry & Resilience** – built with `tenacity` to survive transient network/API issues.
* **Logging** – structured logs stored in `logs/app.log`.
* **CI/CD** – GitHub Actions scheduled run every Monday at 04:00 UTC.
* **Developer Tooling** – [`uv`](https://github.com/astral-sh/uv), [`pre-commit`](https://pre-commit.com/), [`ruff`](https://docs.astral.sh/ruff/), [`mypy`](https://mypy-lang.org/).

---

## 📂 Project Structure

```bash
3mtt-learner-reminder/
|__ .github
|   ├── workflows
|   │   └── scheduler.yml   # Trigger to run the app and send out emails 
                            # based on the set frequency
├── Makefile                # Developer shortcuts
├── README.md
├── __init__.py
├── analysis.ipynb          # Notebook for exploratory analysis
├── assets/                 # Visualizations (charts, infographics)
│   ├── emails_infographic.png
│   ├── learners_bar.png
│   └── learners_donut.png
├── config.py               # Pydantic settings (loads from env vars)
├── data/
|   ├── emails_sent.db      # SQLite database for tracking sent emails
│   └── learners.json       # .gitignored downloaded learner data for analysis
├── data_processing/
│   ├── downloader.py       # API downloader (async, paginated)
│   └── filters.py          # Learner filtering logic
├── email_sender/
│   ├── mailjet_client.py   # Mailjet API wrapper
|   ├── ses_client.py       # AWS SES API wrapper
│   └── templates.py        # HTML email templates
├── log.py                  # Loguru structured logging config
├── main.py                 # Orchestration entrypoint
├── pyproject.toml          # Project dependencies (uv-managed)
├── pytest.ini
├── tests/                  # Unit + integration tests
│   ├── integration/
│   │   ├── test_downloader_async.py
│   │   └── test_filters_async.py
│   └── unit/
│       ├── test_downloader_unit.py
│       ├── test_filters_unit.py
│       └── test_mailjet_client.py
├── utils/                  # Utilities
│   ├── batching.py
│   └── retry.py            # Tenacity retry decorator
|── .env                    # Environment variables
|── .env.example            # Example environment variables
|── .gitignore              # .gitignored files
|__ .pre-commit-config.yaml # Pre-commit hooks
└── uv.lock                 # Dependency lockfile
```

---

## ⚙️ Setup & Installation

### 1. Clone the repository

```bash
git clone git@github.com:<your-org>/3mtt-learner-reminder.git
cd 3mtt-learner-reminder
```

### 2. Install dependencies with `uv`

```bash
uv sync
```

This creates a `.venv/` environment with all dependencies installed.

### 3. Configure environment variables

Copy `.env.example` into `.env` and fill in required values:

```bash
cp .env.example .env
```

---

## ▶️ Running the Project

Run the reminder workflow locally:

```bash
uv run main.py
```

---

## 🧪 Testing

Run all tests:

```bash
pytest
```

Run only unit tests:

```bash
pytest -m unit
```

Run only integration tests:

```bash
pytest -m integration
```

---

## 🧹 Developer Tooling

Pre-commit hooks ensure consistent formatting and type safety.

Run manually:

```bash
make precommit
```

Checks include:

* **Ruff** – linting & formatting
* **Mypy** – static type checking

---

## 🚀 Deployment

The project is deployed via **GitHub Actions**:

* **Schedule**: Every Monday at 04:00 UTC.
* **Manual Trigger**: `workflow_dispatch` enabled.
* **Dependencies**: Managed with `uv`.
* **Secrets**: Loaded from GitHub Actions secrets.

Example workflow file: `.github/workflows/weekly-run.yml`

---

## 📊 Analysis & Visuals

The repo includes:

* `analysis.ipynb` – exploratory data analysis of learners.
* `assets/learners_bar.png` – distribution of learners.
* `assets/learners_donut.png` – activity breakdown.
* `assets/emails_infographic.png` – email workflow illustration.

---

## 🔑 GitHub Secrets Required

Set these in **Settings → Secrets and variables → Actions**:

* `DAREY_USERNAME`, `DAREY_PASSWORD`, `BUSINESS_ID`
* `ORIGIN_EMAIL`, `ORIGIN_NAME`
* `MAILJET_API_KEY`, `MAILJET_API_SECRET`
* `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
* `CONCURRENCY`
* `DOWNLOAD_URL`, `DOWNLOAD_LIMIT`, `BATCH_SIZE`
* `INACTIVE_DAYS`, `LOW_SCORE_THRESHOLD`
* `MAX_RETRIES`, `RETRY_DELAY`
* `TEST_MODE`, `TEST_EMAIL_ADDRESS`, `DRY_RUN`

> **Note:** Set `TEST_MODE` and `DRY_RUN` to `False` in production.

---

## 👨‍💻 Contributing

1. Fork the repo
2. Create your feature branch (`git checkout -b feature/xyz`)
3. Commit changes (`git commit -m 'Add xyz'`)
4. Run checks (`make precommit`)
5. Push branch and open PR

---
