AKIRA — LOCAL DESIGN V2 (NO LIVE DEPLOYMENT)
=============================================

Changes from local v1:
- Removes 'SYSTEMS SECURITY RESEARCH' subtitle and the three interests in the hero.
- Renames 'LATEST WRITEUPS' to 'LAST BLOGPOST'.
- Increases fonts in article code fences, TOC, blockquotes, and captions.
- Adds an 'Upcoming' page driven by data/upcoming.yaml and shown in nav.
- Includes a one-time, idempotent script to clean '; see Linux source'
  in the Dirty Pipe Markdown without deleting the links or URLs.

Installation (from the Hugo project root where hugo.toml is):
  # OPTIONAL: create a local branch first
  git switch -c design/akira-v2

  # The ZIP updates 2 files from v1 (akira.css and home_info.html).
  # Review/save any personal changes to those before overwriting them.
  unzip -o ~/Downloads/akira-hugo-local-v2.zip -d .
  python3 scripts/clean-dirty-pipe-sources.py
  hugo server -D --disableFastRender

Preview locally at http://localhost:1313 and /upcoming/.
DO NOT push/commit until you have reviewed the results.

How to add an upcoming post:
Edit data/upcoming.yaml, using the commented example as a guide.
Use statuses: planned, researching, drafting, reviewing, paused.
Only add titles you want publicly visible. Empty data gives an honest empty state.

The ZIP DOES NOT overwrite hugo.toml, your posts, or the PaperMod submodule.
The cleaning script edits only the exact phrase '; see Linux source'.
Before committing, use: git diff --stat && git diff
