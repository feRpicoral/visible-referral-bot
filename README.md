# visible-referral

A tiny GitHub-Actions-powered bot that posts your **Visible** referral code as a comment on the latest [r/Visible](https://www.reddit.com/r/Visible) biweekly referral megathread.

- Runs daily on a free GitHub Actions cron.
- Idempotent: if you've already commented on the open megathread, it does nothing.
- Picks a different message template each time from `messages.yaml` so your comments aren't identical.
- Posts **one** top-level comment per megathread — Reddit's spam rules apply even in contest-mode threads.

## Fork and go

1. **Fork this repo** on GitHub.

2. **Create a Reddit "script" app** at <https://www.reddit.com/prefs/apps>:
   - Type: **script**
   - Redirect URI: `http://localhost:8080` (unused but required)
   - Save the **client ID** (the short string under the app name) and the **client secret**.

3. **Add these 5 GitHub Secrets** on your fork (Settings → Secrets and variables → Actions → New repository secret):

   | Secret | Value |
   | --- | --- |
   | `REDDIT_CLIENT_ID` | from step 2 |
   | `REDDIT_CLIENT_SECRET` | from step 2 |
   | `REDDIT_USERNAME` | your Reddit username, no `/u/` |
   | `REDDIT_PASSWORD` | your Reddit password (if 2FA is on, use an [app password](https://www.reddit.com/wiki/api)) |
   | `REFERRAL_CODE` | e.g. `69GHWFW` |

4. **Enable Actions** on your fork (GitHub disables them on new forks by default — one click in the Actions tab).

5. *(optional)* Edit `messages.yaml` to rewrite the templates in your own voice.

6. **Test before going live:** Actions → **Post Visible referral** → **Run workflow** → tick **Log the message but don't actually post** → run. Check the log shows the matched megathread title and the formatted message containing your code and link.

7. Uncheck the dry-run box, run again, and verify your comment appears on the megathread.

After that, the daily cron takes over. Each day at 12:00 UTC it checks the subreddit; on the first run after a new megathread is stickied, it posts; on every other run it logs "already commented" and exits.

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env  # fill in your credentials

# Dry-run: prints the message it would post, posts nothing.
DRY_RUN=1 python -m src.main

# Real run.
python -m src.main
```

### Code quality

The repo uses [Ruff](https://docs.astral.sh/ruff/) for both formatting and linting. The same checks run in CI via `.github/workflows/lint.yml`.

```bash
ruff format .            # auto-format
ruff check . --fix       # lint + auto-fix
ruff check .             # check-only (what CI runs)
ruff format --check .    # format-check (what CI runs)
```

## How it finds the megathread

`src/main.py` calls `subreddit.sticky(number=1)` and `subreddit.sticky(number=2)` and matches the title against `(?i)bi-?weekly\s+megathread.*referral\s+codes`. If neither sticky matches (e.g. mods forgot to re-pin), it falls back to scanning the 25 newest posts with the same regex. If nothing matches, it logs and exits 0.

## Caveats

- Reddit and many subreddits auto-remove comments from very new or low-karma accounts. Use a Reddit account with some prior activity.
- If r/Visible's rules ever change to disallow the megathread or your code in it, **kill the workflow**. This bot is intended only for the sub's existing dedicated referral megathread.
- If the megathread title format ever changes significantly, update the regex in `src/main.py`.
