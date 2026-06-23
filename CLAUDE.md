# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A children's storybook (儿童故事绘本) web app: users paste/upload a story, the app splits it into pages, generates an illustration per page, lays out each page with text + image, and exports a readable book + PDF. UI text and code comments are in Chinese; target audience is ages 3–8.

The entire application lives in `children_storybook_app/` (a Flask app). The repo root holds only tooling dirs (`.venv`, `.agents`, `.codex`, `.trae`) and the development plan (`儿童故事绘本应用开发计划.md`).

## Commands

All commands run from `children_storybook_app/`:

```bash
cd children_storybook_app

# Install deps (use the app-local venv, NOT the root .venv)
pip install -r requirements.txt

# Run the dev server -> http://localhost:5000 (debug=True, host 0.0.0.0)
python app.py

# Run the integration test suite (forces offline/local-fallback image mode)
python -m unittest test_offline_flow

# Run a single test
python -m unittest test_offline_flow.OfflineGenerationFlowTest.test_generate_book_without_external_image_api
```

There is no linter/formatter configured and no separate build step.

## Configuration (environment variables)

Set in `config.py` (read from env, with defaults):

- `AGNES_API_KEY` — Agnes Image API key. **If unset, image generation falls back to locally-drawn placeholder illustrations** (see fallback below), so the full flow works with no external API.
- `LOCAL_IMAGE_FALLBACK` (default `true`) — when true, any API failure/timeout/missing-key produces a local placeholder image instead of erroring.
- `IMAGE_SIZE` (default `1024x768`), `IMAGE_TIMEOUT` (default `30`s), `SECRET_KEY`.

The image API endpoint/model (`agnes-image-2.1-flash`) and content limits (`MAX_STORY_LENGTH`, `MAX_CHAPTERS`, style presets) are hardcoded in `config.py`.

## Architecture

The generation flow is a linear pipeline orchestrated by `app.py` route handlers, each stage delegating to one module in `utils/`:

```
story text/file
  -> content_filter.validate_story()   # safety gate (sensitive-word scan)
  -> story_parser.StoryParser          # text -> normalized story dict w/ chapters
  -> image_generator.generate_book_images()  # one illustration per chapter
  -> layout_engine.create_picture_book()      # compose pages -> PNGs + PDF + meta JSON
```

The **story dict** is the central data structure threaded through every stage: `{id, title, author, created_at, chapters: [{title, content}], chapter_count, word_count}`. One chapter == one book page.

### `utils/` modules (each exposes a class + a module-level convenience function + a global singleton)

- **`content_filter.py`** — `ContentFilter` / `validate_story()`. Scans title+author+content against Chinese/English word lists. Returns `{safe, risk_level (low/medium/high), matched_words, score}`. Word lists auto-bootstrap to `data/filters/{chinese,english}_words.txt` on first run from hardcoded defaults; edit those files to customize. `risk_level == "high"` blocks parsing/generation in `app.py`; medium passes with a warning.
- **`story_parser.py`** — `StoryParser` / `parse_text`. Splits raw text into chapters: first tries chapter markers (第X章/Chapter N regex), else by paragraphs, capping at **10 chapters** (overflow merged into the last). Handles `.txt` and `.json` uploads. `create_demo_story()` returns the built-in "小兔子找彩虹" sample.
- **`image_generator.py`** — `ImageGenerator` / `generate_book_images()`. Builds an English prompt from each (Chinese) chapter, calls the Agnes API, downloads + caches the result to `data/images/`. **Caching is by output filename** (`{title}_{id[:8]}_pageN.png`) — re-generating a story reuses existing page images. On any failure it draws a procedural placeholder scene with Pillow (`_generate_local_image`).
- **`layout_engine.py`** — `LayoutEngine` / `create_picture_book()`. Pure Pillow rendering at fixed `1024x768`: builds cover + content pages (left text / right image) + back cover, writes per-page PNGs and a combined PDF to `data/books/`, and writes the book metadata JSON. Page assets are written with random hex suffixes; the canonical record is `data/books/{story_id}.json`.

### Frontend

Server-rendered Jinja templates (`templates/`) + vanilla JS (`static/js/`), one JS file per page: `app.js` (index/input), `editor.js` (editor), `reader.js` (reader). No build tooling — edit and reload.

### Data layout (`children_storybook_app/data/`, gitignored content, auto-created)

- `stories/{id}.json` — saved source stories
- `images/` — generated/cached per-page illustrations
- `books/{id}.json` + `{id}.pdf` + page/cover/back PNGs — finished books
- `filters/` — editable sensitive-word lists

### API surface (`app.py`)

All `/api/*` endpoints return the uniform `{success, message, data}` envelope via `json_response()`. Key routes: `/api/story/{validate,parse,upload,save}`, `/api/book/generate`, `/api/books/{list,<id>,<id>/download}`. Pages: `/`, `/editor`, `/reader/<book_id>`.

## Conventions & gotchas

- **Asset serving is deliberately restricted**: the `/data/<path>` route only serves `books/` and `images/` with image extensions — never story/book JSON. `asset_url()` converts absolute local paths into these browser URLs; `enrich_book_assets()` adds `image_url` fields when returning book detail. Keep this restriction if adding new served asset types.
- **Fonts are hardcoded Windows paths** (`C:/Windows/Fonts/msyh.ttc`, etc.) in both `image_generator.py` and `layout_engine.py`, falling back to Pillow's default font. CJK text renders as boxes if no CJK font is found — add other-OS font paths when running off Windows.
- Two virtualenvs exist (`.venv` at repo root, `children_storybook_app/venv/`). Use the app-local one for running the app; both are committed/ignored noise, don't add files there.
- Tests hit the real pipeline through Flask's test client and write to `data/`, cleaning up afterward; they force offline image mode by clearing `AGNES_API_KEY` at import time.
