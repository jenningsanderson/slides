## Local Development

Requires [uv](https://docs.astral.sh/uv/) — no other setup.

```bash
git clone https://github.com/jenningsanderson/slides
cd slides
uv sync

# All commands go through the unified CLI:
uv run slides --help
```

<div class="two-col">
<div markdown="1">

#### Build & inspect

```bash
uv run slides build
uv run slides outline
uv run slides lint
uv run slides watch
```

</div>
<div markdown="1">

#### Dev server

```bash
# Live-reload at http://localhost:3000
uv run slides serve

# Custom port
uv run slides serve --port 8080
```

</div>
</div>

Note:
uv handles the virtual environment automatically. The first uv sync downloads
markdown and (optionally) Pillow + numpy for the terminal-gif tool.

---

## Project Layout

```
your-repo/
├── slides/           ← markdown source files (01-intro.md, 02-demo.md …)
├── css/              ← optional custom CSS (overrides action default)
├── assets/           ← images, JSON sessions, terminal-player.js
├── .github/
│   └── workflows/
│       └── pages.yml
└── index.html        ← built output (gitignored)
```

#### Custom theme

Drop any `.css` file into `css/` — it is loaded automatically.
The action uses your `css/` dir if it exists, otherwise falls back to the
built-in `default.css`.

Note:
Keep css/ and assets/ in the same directory as slides/. The action copies
them both into the output directory so all paths are relative and the
presentation works offline.
