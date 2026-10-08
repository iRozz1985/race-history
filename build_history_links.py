"""Build a 'race history quick links' page (index.html) for GitHub Pages.

For each UK/Ireland meeting on today's card, this lists the races (time + course)
and gives one-click links to that course's results archive and racecard on
At The Races and the Racing Post, where you can look up:
  - past winners of races at that course (browse previous dates)
  - a race's previous runnings and the trainers who have won it

Why links rather than computed trends: a decade of race results is premium data
that isn't freely/reliably available, so instead of scraping it, this tool points
you straight at the pages that already show the history. Today's card comes from
the free Ladbrokes feed; no paid API, no scraping.

Runs on a schedule via GitHub Actions each morning, using the Ladbrokes API key
stored as the LADS_API_KEY GitHub Secret.

Usage (local test):
    set LADS_API_KEY=...        (Windows cmd) / $env:LADS_API_KEY (PowerShell)
    python build_history_links.py
"""

import argparse
import html
import urllib.parse
from collections import defaultdict
from datetime import datetime, date
from zoneinfo import ZoneInfo

import console_utf8  # noqa: F401
from lads_client import LadsClient, detect_country, parse_event_name


# Markers that indicate a special bet market rather than a real meeting.
_NOT_A_MEETING = ("double", "treble", "quickfire", "accumulator", "enhanced",
                  "quaddie", "placepot", "jackpot", "scoop")


def _is_real_meeting(track: str) -> bool:
    """True if `track` looks like a genuine racecourse name, not a bet special."""
    t = track.strip().lower()
    if not t or t.startswith("&") or t.startswith("+"):
        return False
    return not any(word in t for word in _NOT_A_MEETING)


def _race_day(event: dict):
    """The race's local (UK) calendar date from eventDateTime, or None."""
    dt_str = event.get("eventDateTime", "") or ""
    if not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.astimezone(UK_TZ).date()
    except (ValueError, TypeError):
        return None

UK_TZ = ZoneInfo("Europe/London")

# Our course names (from the Ladbrokes feed) -> At The Races results slug.
# Most are identical; only the ones that differ need listing. The ATR results
# URL is https://www.attheraces.com/results/<slug>.
ATR_SLUG = {
    "Kempton Park": "Kempton",
    "Sandown Park": "Sandown",
    "Haydock Park": "Haydock",
    "Hamilton Park": "Hamilton",
    "Fontwell Park": "Fontwell",
    "Lingfield Park": "Lingfield",
    "Epsom Downs": "Epsom",
    "Bangor-on-Dee": "Bangor",
    "Stratford-on-Avon": "Stratford",
    "Market Rasen": "Market-Rasen",
    "Newton Abbot": "Newton-Abbot",
    "Down Royal": "Down-Royal",
    "Gowran Park": "Gowran-Park",
}


def atr_slug(track: str) -> str:
    if track in ATR_SLUG:
        return ATR_SLUG[track]
    # Default: the track name with spaces as hyphens (ATR uses hyphens).
    return track.replace(" ", "-")


def atr_results_url(track: str) -> str:
    return "https://www.attheraces.com/results/" + atr_slug(track)


def atr_racecard_url(track: str) -> str:
    return "https://www.attheraces.com/racecard/" + atr_slug(track)


def rp_course_search_url(track: str) -> str:
    # Racing Post results search for the course name (lands on the course's
    # results; from there you can pick previous dates / races).
    q = urllib.parse.quote(track)
    return "https://www.racingpost.com/results/search-results/?searchTerm=" + q


def collect_meetings(countries, target_day):
    """Return {track: {"country": c, "races": [time,...]}} for target_day only."""
    client = LadsClient()
    events = client.get_all_real_events()
    country_set = {c.upper() for c in countries}

    meetings = defaultdict(lambda: {"country": "", "races": []})
    for e in events:
        time_str, track, _ = parse_event_name(e.get("eventName", ""))
        if not time_str or not track:
            continue
        # Skip special bet markets (e.g. "... & 14:30 Enhanced Quickfire Double")
        # which aren't real meetings but parse into junk track names.
        if not _is_real_meeting(track):
            continue
        country = detect_country(e)
        if country not in country_set:
            continue
        # Only keep races on the target calendar day (the feed carries future
        # days too once declarations are made).
        rday = _race_day(e)
        if rday is not None and rday != target_day:
            continue
        meetings[track]["country"] = country
        if time_str not in meetings[track]["races"]:
            meetings[track]["races"].append(time_str)
    for t in meetings:
        meetings[t]["races"].sort()
    return meetings


def build_html(meetings):
    esc = html.escape
    generated = datetime.now(UK_TZ).strftime("%A %d %B %Y, %H:%M %Z")

    if not meetings:
        body = ("<p class='none'>No UK or Irish meetings found on today's card "
                "right now. Check back later, or during racing hours.</p>")
    else:
        blocks = ""
        for track in sorted(meetings):
            info = meetings[track]
            races = info["races"]
            times = " &middot; ".join(esc(t) for t in races)
            blocks += (
                "<div class='meeting'>"
                f"<h2>{esc(track)} <span class='ctry'>{esc(info['country'])}"
                f"</span> <span class='rc'>{len(races)} race"
                f"{'s' if len(races) != 1 else ''}</span></h2>"
                f"<div class='times'>{times}</div>"
                "<div class='links'>"
                f"<a href='{esc(atr_results_url(track))}' target='_blank' rel='noopener'>"
                "Past results &amp; winners (At The Races)</a>"
                f"<a href='{esc(atr_racecard_url(track))}' target='_blank' rel='noopener'>"
                "Today's racecard</a>"
                f"<a href='{esc(rp_course_search_url(track))}' target='_blank' rel='noopener'>"
                "Search on Racing Post</a>"
                "</div>"
                "</div>"
            )
        count = len(meetings)
        body = (f"<p class='count'>{count} UK &amp; Irish meeting"
                f"{'s' if count != 1 else ''} today &middot; tap a meeting to "
                "look up its history</p>" + blocks)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Race History Links</title>
<style>
  :root {{ --blue:#4ec3ff; --ink:#1b2733; --muted:#64748b; --line:#e2e8f0; --bg:#f1f5f9; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,
         Helvetica,Arial,sans-serif; background:var(--bg); color:var(--ink); }}
  header {{ background:var(--blue); color:#063047; padding:18px 20px; }}
  header h1 {{ margin:0; font-size:22px; }}
  header p {{ margin:4px 0 0; font-size:13px; color:#0a3f5c; }}
  main {{ padding:16px 20px 40px; }}
  .count {{ font-size:15px; font-weight:700; margin:6px 0 14px; }}
  .none {{ font-size:16px; color:var(--muted); background:#fff; border:1px solid var(--line);
          border-radius:10px; padding:18px; }}
  .meeting {{ background:#fff; border:1px solid var(--line); border-radius:10px;
             padding:12px 14px; margin-bottom:12px; }}
  .meeting h2 {{ margin:0 0 4px; font-size:17px; }}
  .ctry {{ color:var(--muted); font-size:12px; font-weight:400; }}
  .rc {{ color:var(--muted); font-size:12px; font-weight:400; float:right; }}
  .times {{ color:#334155; font-size:13px; margin-bottom:10px; }}
  .links {{ display:flex; flex-wrap:wrap; gap:8px; }}
  .links a {{ display:inline-block; background:#eaf7ff; color:#06324a;
             border:1px solid #bfe4fb; border-radius:8px; padding:7px 11px;
             font-size:13px; text-decoration:none; font-weight:600; }}
  .links a:hover {{ background:#d8f0ff; }}
  footer {{ padding:0 20px 30px; font-size:12px; color:var(--muted); }}
  footer a {{ color:var(--muted); }}
</style>
</head>
<body>
<header>
  <h1>Race History Links</h1>
  <p>Today's UK &amp; Irish meetings &middot; quick links to past winners,
     previous runnings and trainer records</p>
</header>
<main>
  {body}
</main>
<footer>
  Updated {esc(generated)} &middot; today's card from the Ladbrokes feed &middot;
  history links open <a href="https://www.attheraces.com" target="_blank" rel="noopener">At The Races</a>
  and <a href="https://www.racingpost.com" target="_blank" rel="noopener">Racing Post</a>.
  Use each course's date picker there to see previous years.
</footer>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description="Build the race-history quick-links page")
    ap.add_argument("--countries", default="UK,IRE")
    ap.add_argument("--output", default="index.html")
    args = ap.parse_args()

    countries = tuple(c.strip().upper() for c in args.countries.split(",") if c.strip())
    today = datetime.now(UK_TZ).date()
    print(f"Collecting today's meetings ({'/'.join(countries)}) for {today}...")
    meetings = collect_meetings(countries, today)
    print(f"Meetings found: {len(meetings)}")

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(build_html(meetings))
    print(f"Wrote {args.output} with {len(meetings)} meeting(s).")


if __name__ == "__main__":
    main()
