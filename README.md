# Akira — Security Research Blog

Hugo ([PaperMod](https://github.com/adityatelange/hugo-PaperMod)) static site,
auto-deployed to GitHub Pages via GitHub Actions.

---

## Push it live (first time)

```bash
# 1. Create an EMPTY repo on GitHub (no README/license).
#    - For the root URL (https://misterz.github.io/), name it:  misterz.github.io
#    - Any other name (e.g. "blog") also works → URL becomes .../blog/.
#      The deploy workflow handles the subpath automatically; nothing to edit.

# 2. Point this repo at it and push:
git remote add origin git@github.com:Misterz/<REPO_NAME>.git   # or the https URL
git branch -M main
git push -u origin main

# 3. On GitHub:  Settings → Pages → "Build and deployment" → Source: GitHub Actions
#    (do this once; the workflow in .github/workflows/hugo.yml does the rest.)
```

Every `git push` to `main` rebuilds and redeploys. Watch it in the **Actions** tab;
the live URL shows up under the **deploy** job when it finishes.

> **Note on `baseURL`:** the *deployed* site always gets the right URL — the
> workflow pulls it from GitHub Pages at build time. The `baseURL` in `hugo.toml`
> only affects local builds.

### Adding a custom domain later (optional)

Not set up now — the site runs on `misterz.github.io`. To switch to a custom
domain (e.g. `akira.sh`) whenever you want:

1. Create `static/CNAME` containing just the domain (e.g. `akira.sh`), and set
   `baseURL` in `hugo.toml` to `https://akira.sh/`.
2. At your registrar, point DNS at GitHub Pages — apex: four `A` records to
   `185.199.108.153` … `185.199.111.153` (plus `AAAA` for IPv6); or a `www`
   `CNAME` → `misterz.github.io.`. (Note: some `.sh` registrars don't allow apex
   `A` records — if so, host on `www.` instead.)
3. GitHub → **Settings → Pages → Custom domain** → enter it → **Save** → tick
   **Enforce HTTPS** once the cert provisions.

---

## Write / preview locally

Requires **Hugo extended** (v0.167.0 to match the deploy; PaperMod needs ≥ 0.146.0).

```bash
# Clone WITH the theme submodule:
git clone --recurse-submodules git@github.com:Misterz/<REPO_NAME>.git
# (already cloned without it?  →  git submodule update --init --recursive)

hugo server -D            # live preview at http://localhost:1313  (-D shows drafts)
```

### The writeup

`content/posts/babyqemu-qemu-escape.md` is a skeleton — your six sections as
headers with placeholder code/figure blocks and `TODO` markers. Fill it in:

```bash
grep -rn TODO content/    # everything left to write
```

- Front matter controls `title`, `date`, `tags`, `summary`, and `draft`.
- Set `draft: true` while writing so it won't publish; flip to `false` (or delete
  the line) when it's ready. The file ships as `draft: false`.
- Images: drop them in `static/images/` and reference `/images/foo.png`, or make
  the post a page bundle (a folder with `index.md`) and keep images beside it.
- New post later:  `hugo new posts/my-title.md`

### Things you might tweak

| What | Where |
|------|-------|
| Site title / description / landing blurb | `hugo.toml` → `title`, `params.homeInfoParams` |
| Social links (GitHub, email, RSS) | `hugo.toml` → `params.socialIcons` |
| Nav menu | `hugo.toml` → `[menu]` |
| Code color scheme | `hugo.toml` → `markup.highlight.style` (try `dracula`, `nord`, `github-dark`) |
| About page | `content/about.md` |

---

## Layout

```
.
├── .github/workflows/hugo.yml   # CI: build + deploy to Pages
├── hugo.toml                    # site config
├── content/
│   ├── about.md
│   ├── archives.md              # /archives/  (auto list of all posts)
│   ├── search.md                # /search/    (client-side fuzzy search)
│   └── posts/
│       └── babyqemu-qemu-escape.md   # ← your writeup skeleton
└── themes/PaperMod/             # theme (git submodule — don't edit in place)
```
