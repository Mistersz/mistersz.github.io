# Akira — Security Research Blog

Hugo ([PaperMod](https://github.com/adityatelange/hugo-PaperMod)) static site,
auto-deployed to GitHub Pages via GitHub Actions.

---

## Push it live (first time)

Site is configured for the custom domain **`akira.sh`** (apex). The `static/CNAME`
file in this repo binds it; you just need the repo pushed and DNS pointed.

```bash
# 1. Create an EMPTY repo on GitHub (no README/license). Name it anything —
#    with a custom domain the repo name doesn't affect the URL. (e.g. "blog")

# 2. Point this repo at it and push:
git remote add origin git@github.com:Misterz/<REPO_NAME>.git   # or the https URL
git branch -M main
git push -u origin main

# 3. On GitHub:  Settings → Pages → "Build and deployment" → Source: GitHub Actions
#    (do this once; the workflow in .github/workflows/hugo.yml does the rest.)
```

### Point `akira.sh` at GitHub Pages (DNS)

At your registrar for `akira.sh`, create these records:

| Type   | Host / Name | Value                 |
|--------|-------------|-----------------------|
| `A`    | `@`         | `185.199.108.153`     |
| `A`    | `@`         | `185.199.109.153`     |
| `A`    | `@`         | `185.199.110.153`     |
| `A`    | `@`         | `185.199.111.153`     |
| `AAAA` | `@`         | `2606:50c0:8000::153` |
| `AAAA` | `@`         | `2606:50c0:8001::153` |
| `AAAA` | `@`         | `2606:50c0:8002::153` |
| `AAAA` | `@`         | `2606:50c0:8003::153` |
| `CNAME`| `www`       | `misterz.github.io.`  |

- The four `A` (and matching `AAAA` for IPv6) records point the **apex** `akira.sh`
  at Pages. The `www` `CNAME` is optional but recommended — GitHub auto-redirects
  `www.akira.sh` → `akira.sh`.
- `.sh` registrars sometimes don't allow apex `A` records (no "ALIAS/ANAME"
  support). If yours doesn't, the fallback is to host on `www.akira.sh` instead:
  make `www` the custom domain in Pages settings, put `www.akira.sh` in
  `static/CNAME`, and keep only the `www` `CNAME` record above.

### Finish on GitHub

1. **Settings → Pages → Custom domain** → enter `akira.sh` → **Save**.
   (GitHub runs a DNS check; it goes green once the records above propagate —
   usually minutes, up to ~an hour.)
2. Once green, tick **Enforce HTTPS** (waits for the TLS cert to provision).

Every `git push` to `main` rebuilds and redeploys. Watch it in the **Actions** tab.

> **How the domain binds:** `static/CNAME` → published as `/CNAME` on every build,
> which is what tells Pages to serve the site at `akira.sh`. The deploy workflow
> also reads the domain back from Pages and feeds it to Hugo as `--baseURL`, so
> generated links are correct. Don't delete the `CNAME` file — a build without it
> resets the custom domain in Pages settings.

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
