# 3MTT Learner Reminder Service

This repository contains the code for sending weekly email reminders to learners in the 3MTT program who have been inactive or have low progress scores.

## Features

- Fetch learners via Darey API
- Filter based on last login and score thresholds
- Send templated emails using Mailjet
- Tested and scheduled via GitHub Actions / Lambda

## Usage

1. Add `.env` or CI secrets.
2. Run `python main.py`.
3. To test locally: `uv run pre-commit run --all-files`.
