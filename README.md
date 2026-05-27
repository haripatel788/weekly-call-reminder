# Weekly call reminder

Python script reads [Google Sheets](https://developers.google.com/sheets/api) roster and logs, assigns three roles for the upcoming Tuesday, updates the sheet, and posts a reminder to Telegram.

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BOT_TOKEN` | Yes | Telegram bot token |
| `CHAT_ID` | Yes | Destination chat id (integer string) |
| `THREAD_ID` | No | Forum topic / thread id; omit for non-forum chats |
| `GCP_CREDENTIALS` | Yes | JSON string for a Google service account with access to the spreadsheet |

## Local run

```bash
pip install -r requirements.txt
export BOT_TOKEN=... CHAT_ID=... GCP_CREDENTIALS='{"type":"service_account",...}'
python bot.py
```

## Scheduling (replacing GitHub Actions)

GitHub-hosted `schedule` workflows are best-effort and can queue for a long time. Prefer one of these:

1. **Machine cron** (VPS, Mac mini, always-on PC): run the same command on your clock, e.g. `crontab -e` with `cd /path/to/repo && /usr/bin/python3 bot.py` and env loaded from a file only readable by your user.
2. **Docker + cron**: build this image, then `docker run --rm --env-file /secure/path/weekly.env your-registry/weekly-call-reminder:latest`.
3. **Google Cloud**: build and push the image from the `Dockerfile`, create a [Cloud Run job](https://cloud.google.com/run/docs/create-jobs), inject secrets via [Secret Manager](https://cloud.google.com/run/docs/configuring/secrets), then attach a schedule with [Cloud Scheduler executing the job](https://cloud.google.com/run/docs/execute/jobs-on-schedule) (tighter timing than GitHub Actions).

The GitHub workflow in this repo keeps **workflow_dispatch** only so you can still trigger a manual run from the Actions tab if needed.
