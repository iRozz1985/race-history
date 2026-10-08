# Race History Links

A simple morning page that lists **today's UK & Irish race meetings** and, for
each course, gives one-click links to look up its **past results, previous
winners and trainer records** on At The Races and the Racing Post.

## Why links instead of computed trends

A decade of race results is premium data that isn't freely or reliably
available (the open APIs paywall it, and scraping it is fragile and against
site terms). Rather than build on shaky foundations, this tool points you
straight at the pages that already show the history. You get the convenience of
a single daily page without any paid data feed or scraping.

- **Today's meetings** come from the free Ladbrokes feed.
- **History links** open the course's results archive on
  [At The Races](https://www.attheraces.com) (which has a date picker to browse
  previous years) and a Racing Post search.

## How it works

| Piece | What it does |
|-------|--------------|
| `build_history_links.py` | Reads today's UK/Irish card and writes `index.html` with a card per meeting and its history links. |
| `lads_client.py`, `racing_query.py` | Ladbrokes API client + helpers (reads the key from `LADS_API_KEY`). |
| `.github/workflows/update-history-links.yml` | Runs the builder each morning (~07:00 UK) and commits the page. |

The build is light (one metadata call), so it runs in seconds.

## One-time setup

### 1. Create the repo and upload these files
Upload everything in this folder, **including the hidden `.github` folder**. If
the hidden folder is awkward, create the workflow file in GitHub's web editor:
**Add file -> Create new file**, name it
`.github/workflows/update-history-links.yml`, paste the contents.

### 2. Add your Ladbrokes API key as a secret
1. **Settings -> Secrets and variables -> Actions -> New repository secret**.
2. Name: `LADS_API_KEY`
3. Value: your Ladbrokes API key.

### 3. Enable GitHub Pages
**Settings -> Pages -> Deploy from a branch -> main -> / (root) -> Save**.

### 4. Build the first page
**Actions -> Update race history links -> Run workflow.** Green tick, then
reload your Pages URL.

## Running locally (optional)

```bash
pip install -r requirements.txt
set LADS_API_KEY=your_key_here       # PowerShell: $env:LADS_API_KEY="..."
python build_history_links.py
```

Then open `index.html`.

## Notes

- Links go to each course's results page; use the **date picker** there to view
  previous years' runnings and see which trainers have won.
- Special bet markets (e.g. "Enhanced Quickfire Double") are filtered out so
  only real meetings appear.
- Course-name links use the common course name; the odd course may need its
  slug adjusting in `ATR_SLUG` inside `build_history_links.py` if a link 404s.
