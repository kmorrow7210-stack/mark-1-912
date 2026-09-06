#!/usr/bin/env python3
"""Local Markdown preview server for the Mark 1 study notes.

Renders the repository's Markdown files as styled HTML so an author can see
formatted output (headings, tables, footnotes, Greek text) while editing.

Usage:
    python3 tools/preview_server.py [--host HOST] [--port PORT] [--root DIR]

Nothing here modifies repository files; it is a read-only preview.
"""

from __future__ import annotations

import argparse
import html
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import markdown

MD_EXTENSIONS = [
    "extra",          # tables, fenced code, footnotes, etc.
    "sane_lists",
    "toc",
    "admonition",
    "pymdownx.superfences",
]

PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, serif;
    line-height: 1.6; max-width: 820px; margin: 0 auto; padding: 2rem 1.25rem 5rem;
    color: #1b1b1b; background: #fafafa;
  }}
  @media (prefers-color-scheme: dark) {{
    body {{ color: #e6e6e6; background: #16181d; }}
    a {{ color: #7bb2ff; }}
    code, pre {{ background: #23262e; }}
    .topbar {{ border-bottom-color: #2b2f38; }}
  }}
  h1, h2, h3, h4 {{ line-height: 1.25; }}
  a {{ color: #1a5fb4; }}
  code, pre {{ background: #eef0f3; border-radius: 4px; }}
  code {{ padding: 0.1rem 0.3rem; font-size: 0.95em; }}
  pre {{ padding: 0.8rem 1rem; overflow-x: auto; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
  th, td {{ border: 1px solid #b9bdc4; padding: 0.45rem 0.7rem; text-align: left; }}
  blockquote {{ border-left: 4px solid #b9bdc4; margin: 1rem 0; padding: 0.2rem 1rem; color: #555; }}
  .topbar {{ margin-bottom: 1.5rem; padding-bottom: 0.75rem; border-bottom: 1px solid #d0d3d8; }}
  .topbar a {{ text-decoration: none; font-weight: 600; }}
  .filelist li {{ margin: 0.35rem 0; }}
</style>
</head>
<body>
<div class="topbar"><a href="/">&larr; All notes</a></div>
{body}
</body>
</html>
"""


def build_index(root: Path) -> str:
    files = sorted(p for p in root.glob("*.md") if p.is_file())
    items = []
    for f in files:
        href = "/view?" + urllib.parse.urlencode({"path": f.name})
        items.append(f'<li><a href="{html.escape(href)}">{html.escape(f.name)}</a></li>')
    body = (
        "<h1>Mark 1 &mdash; study notes preview</h1>"
        "<p>Select a Markdown file to see it rendered as HTML.</p>"
        f'<ul class="filelist">{"".join(items)}</ul>'
    )
    return PAGE_TEMPLATE.format(title="Mark 1 notes", body=body)


def render_markdown(root: Path, rel_path: str) -> tuple[int, str]:
    # Prevent path traversal: only allow files directly under root.
    candidate = (root / rel_path).resolve()
    if candidate.parent != root.resolve() or candidate.suffix.lower() != ".md" or not candidate.is_file():
        return 404, PAGE_TEMPLATE.format(title="Not found", body="<h1>404</h1><p>No such note.</p>")
    text = candidate.read_text(encoding="utf-8")
    rendered = markdown.markdown(text, extensions=MD_EXTENSIONS)
    body = f"<article>{rendered}</article>"
    return 200, PAGE_TEMPLATE.format(title=candidate.name, body=body)


class Handler(BaseHTTPRequestHandler):
    root: Path = Path(".")

    def _send(self, code: int, body: str) -> None:
        payload = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self._send(200, build_index(self.root))
        elif parsed.path == "/healthz":
            self._send(200, "ok")
        elif parsed.path == "/view":
            params = urllib.parse.parse_qs(parsed.query)
            rel = params.get("path", [""])[0]
            code, body = render_markdown(self.root, rel)
            self._send(code, body)
        else:
            self._send(404, PAGE_TEMPLATE.format(title="Not found", body="<h1>404</h1>"))

    def log_message(self, fmt: str, *args) -> None:
        print("[preview] " + (fmt % args))


def main() -> None:
    parser = argparse.ArgumentParser(description="Markdown preview server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    args = parser.parse_args()

    Handler.root = Path(args.root).resolve()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"[preview] Serving Markdown from {Handler.root} at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[preview] shutting down")
        server.shutdown()


if __name__ == "__main__":
    main()
