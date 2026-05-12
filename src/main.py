"""Post a Visible referral comment on the latest r/Visible biweekly megathread.

Runs idempotently from GitHub Actions on a daily schedule: if a referral
megathread is open and we haven't commented on it yet, post a randomly chosen
template from messages.yaml. Otherwise, do nothing.
"""

import logging
import os
import random
import re
import sys
from pathlib import Path

import praw
import prawcore
import yaml
from praw.models import Submission, Subreddit

SUBREDDIT_NAME = "Visible"
TITLE_REGEX = re.compile(r"(?i)bi-?weekly\s+megathread.*referral\s+codes")
NEW_FALLBACK_LIMIT = 25
MESSAGES_PATH = Path(__file__).resolve().parent.parent / "messages.yaml"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("visible-referral")


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        log.error("Missing required environment variable: %s", name)
        sys.exit(1)
    return value


def load_templates() -> list[str]:
    data = yaml.safe_load(MESSAGES_PATH.read_text())
    templates = data.get("templates") if isinstance(data, dict) else None
    if not templates:
        log.error("No templates found in %s", MESSAGES_PATH)
        sys.exit(1)
    return templates


def find_megathread(subreddit: Subreddit) -> Submission | None:
    for n in (1, 2):
        try:
            sticky = subreddit.sticky(number=n)
        except prawcore.exceptions.NotFound:
            continue
        if TITLE_REGEX.search(sticky.title):
            log.info("Matched sticky #%d: %s", n, sticky.title)
            return sticky

    log.info("Stickies didn't match; scanning new(%d)...", NEW_FALLBACK_LIMIT)
    for submission in subreddit.new(limit=NEW_FALLBACK_LIMIT):
        if TITLE_REGEX.search(submission.title):
            log.info("Matched recent post: %s", submission.title)
            return submission

    return None


def already_commented(submission: Submission, username: str) -> bool:
    submission.comments.replace_more(limit=0)
    target = username.lower()
    for comment in submission.comments:
        author = comment.author
        if author and author.name.lower() == target:
            log.info("Already commented at https://www.reddit.com%s", comment.permalink)
            return True
    return False


def main() -> int:
    client_id = require_env("REDDIT_CLIENT_ID")
    client_secret = require_env("REDDIT_CLIENT_SECRET")
    username = require_env("REDDIT_USERNAME")
    password = require_env("REDDIT_PASSWORD")
    code = require_env("REFERRAL_CODE")
    dry_run = os.environ.get("DRY_RUN") == "1"

    link = f"https://www.visible.com/get/?{code}"
    templates = load_templates()

    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        username=username,
        password=password,
        user_agent=f"r/{SUBREDDIT_NAME} referral bot by /u/{username}",
    )
    reddit.validate_on_submit = True

    subreddit = reddit.subreddit(SUBREDDIT_NAME)
    submission = find_megathread(subreddit)
    if submission is None:
        log.info("No megathread found in r/%s, nothing to do.", SUBREDDIT_NAME)
        return 0

    log.info(
        "Found megathread: %s (https://www.reddit.com%s)",
        submission.title,
        submission.permalink,
    )

    if already_commented(submission, username):
        return 0

    body = random.choice(templates).format(code=code, link=link)

    if dry_run:
        log.info("DRY RUN — would post:\n%s", body)
        return 0

    comment = submission.reply(body)
    log.info("Posted comment: https://www.reddit.com%s", comment.permalink)
    return 0


if __name__ == "__main__":
    sys.exit(main())
