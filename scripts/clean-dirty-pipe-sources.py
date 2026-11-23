#!/usr/bin/env python3
"""One-time, idempotent copy edit. Run from the Hugo project root.
Keeps Markdown source links and URLs intact; edits only the visible phrase.
"""
from pathlib import Path
import re

post = Path("content/posts/dirty-pipe.md")
if not post.is_file():
    raise SystemExit(f"Not found: {post}. Run this from your Hugo project root.")
original = post.read_text(encoding="utf-8")
updated, count = re.subn(r";\s*see Linux source", "", original, flags=re.IGNORECASE)
if count:
    post.write_text(updated, encoding="utf-8")
print(f"Cleaned {count} source label(s) in {post}; original URLs preserved.")
