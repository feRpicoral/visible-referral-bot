"""Tests for the bot logic in src.main."""

from unittest.mock import MagicMock

import prawcore
import pytest

from src.main import (
    TITLE_REGEX,
    already_commented,
    find_megathread,
    require_env,
)

# ---------------------------------------------------------------------------
# TITLE_REGEX
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "title",
    [
        "Biweekly Megathread for Referral Codes - Please post your codes here!",
        "Bi-weekly Megathread for Referral Codes",
        "BIWEEKLY MEGATHREAD FOR REFERRAL CODES",
        "biweekly megathread for referral codes (Q1)",
        "Bi-Weekly  Megathread  for  Referral  Codes",
    ],
)
def test_title_regex_matches_megathreads(title):
    assert TITLE_REGEX.search(title)


@pytest.mark.parametrize(
    "title",
    [
        "Daily discussion thread",
        "Megathread: Coverage Map Updates",
        "Random user post about Visible",
        "Weekly Megathread for Referral Codes",  # not bi-weekly
        "Biweekly Megathread for Coverage Issues",  # wrong topic
    ],
)
def test_title_regex_does_not_match_unrelated(title):
    assert not TITLE_REGEX.search(title)


# ---------------------------------------------------------------------------
# require_env
# ---------------------------------------------------------------------------


def test_require_env_returns_value(monkeypatch):
    monkeypatch.setenv("VISIBLE_TEST_VAR", "bar")
    assert require_env("VISIBLE_TEST_VAR") == "bar"


def test_require_env_exits_when_missing(monkeypatch):
    monkeypatch.delenv("VISIBLE_TEST_VAR", raising=False)
    with pytest.raises(SystemExit) as exc_info:
        require_env("VISIBLE_TEST_VAR")
    assert exc_info.value.code == 1


def test_require_env_exits_when_empty(monkeypatch):
    monkeypatch.setenv("VISIBLE_TEST_VAR", "")
    with pytest.raises(SystemExit) as exc_info:
        require_env("VISIBLE_TEST_VAR")
    assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# already_commented
# ---------------------------------------------------------------------------


def _mock_comment(username, permalink="/r/Visible/comments/xyz/_/abc"):
    comment = MagicMock()
    if username is None:
        comment.author = None
    else:
        comment.author = MagicMock()
        comment.author.name = username
    comment.permalink = permalink
    return comment


def _mock_submission(comments):
    submission = MagicMock()
    submission.comments.replace_more = MagicMock(return_value=None)
    submission.comments.__iter__ = MagicMock(return_value=iter(comments))
    return submission


def test_already_commented_finds_username_case_insensitively():
    sub = _mock_submission([_mock_comment("alice"), _mock_comment("BOB")])
    assert already_commented(sub, "bob") is True


def test_already_commented_handles_deleted_author():
    sub = _mock_submission([_mock_comment(None), _mock_comment("carol")])
    assert already_commented(sub, "dave") is False


def test_already_commented_returns_false_when_absent():
    sub = _mock_submission([_mock_comment("alice"), _mock_comment("bob")])
    assert already_commented(sub, "eve") is False


def test_already_commented_returns_false_when_no_comments():
    sub = _mock_submission([])
    assert already_commented(sub, "anyone") is False


# ---------------------------------------------------------------------------
# find_megathread
# ---------------------------------------------------------------------------


def _mock_submission_with_title(title):
    sub = MagicMock()
    sub.title = title
    return sub


def _mock_subreddit(sticky1=None, sticky2=None, new_posts=None):
    """Subreddit mock; pass None for a sticky slot to make it raise NotFound."""

    def sticky(number=1):
        target = sticky1 if number == 1 else sticky2
        if target is None:
            raise prawcore.exceptions.NotFound(MagicMock())
        return target

    subreddit = MagicMock()
    subreddit.sticky = MagicMock(side_effect=sticky)
    subreddit.new = MagicMock(return_value=iter(new_posts or []))
    return subreddit


def test_find_megathread_returns_first_sticky_when_matching():
    s1 = _mock_submission_with_title("Biweekly Megathread for Referral Codes")
    s2 = _mock_submission_with_title("Some other sticky")
    sub = _mock_subreddit(sticky1=s1, sticky2=s2)
    assert find_megathread(sub) is s1


def test_find_megathread_returns_second_sticky_when_first_does_not_match():
    s1 = _mock_submission_with_title("Some other sticky")
    s2 = _mock_submission_with_title("Biweekly Megathread for Referral Codes")
    sub = _mock_subreddit(sticky1=s1, sticky2=s2)
    assert find_megathread(sub) is s2


def test_find_megathread_falls_back_to_new_when_no_stickies_match():
    s1 = _mock_submission_with_title("Some other sticky")
    s2 = _mock_submission_with_title("Yet another sticky")
    new_match = _mock_submission_with_title("Bi-weekly Megathread for Referral Codes")
    sub = _mock_subreddit(
        sticky1=s1,
        sticky2=s2,
        new_posts=[_mock_submission_with_title("unrelated"), new_match],
    )
    assert find_megathread(sub) is new_match


def test_find_megathread_returns_none_when_nothing_matches():
    s1 = _mock_submission_with_title("Random sticky")
    sub = _mock_subreddit(
        sticky1=s1,
        new_posts=[_mock_submission_with_title("Daily discussion")],
    )
    assert find_megathread(sub) is None


def test_find_megathread_handles_missing_second_sticky():
    s1 = _mock_submission_with_title("Random sticky")
    sub = _mock_subreddit(sticky1=s1, sticky2=None, new_posts=[])
    assert find_megathread(sub) is None


def test_find_megathread_handles_no_stickies_at_all():
    sub = _mock_subreddit(sticky1=None, sticky2=None, new_posts=[])
    assert find_megathread(sub) is None
