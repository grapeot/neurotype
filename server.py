#!/usr/bin/env python3
"""Neurotype local server.

    python server.py            # then open http://127.0.0.1:8000

Serves the typing app (app/), the recorded results (results/), and one API:

    POST /api/correct  {"text": "...", "version": "v2"}  ->  {"output", "rationale", ...}
    GET  /api/versions                                   ->  ["v0", "v1", ...]

The API key stays on the server (read from .env or the environment).
The browser never sees it. Standard library only, no web framework.
"""

from __future__ import annotations

import json
import os
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from neurotype import llm
from neurotype.corrector import correct, list_versions

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app"
RESULTS = ROOT / "results"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(APP), **kwargs)

    def translate_path(self, path: str) -> str:
        clean = urlparse(path).path
        if clean.startswith("/results/"):
            target = (RESULTS / clean[len("/results/"):]).resolve()
            if RESULTS.resolve() in target.parents or target == RESULTS.resolve():
                return str(target)
        return super().translate_path(path)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _json(self, status: int, payload: dict | list) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if urlparse(self.path).path == "/api/versions":
            self._json(200, {"versions": list_versions(), "model": llm.model_name()})
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/api/correct":
            self._json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            req = json.loads(self.rfile.read(length) or b"{}")
            text = str(req.get("text", ""))[:2000]
            versions = list_versions()
            version = req.get("version") or versions[-1]
            if version not in versions:
                self._json(400, {"error": f"unknown version {version}"})
                return
            start = time.time()
            res = correct(version, text)
            self._json(200, {
                "version": version,
                "model": "none" if version == "v0" else llm.model_name(),
                "output": res["output"],
                "rationale": res["rationale"],
                "parse_error": res["parse_error"],
                "latency_s": round(time.time() - start, 2),
            })
        except Exception as exc:  # report, don't crash the server
            self._json(500, {"error": str(exc)})


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Neurotype running at http://127.0.0.1:{port}  (model: {llm.model_name()})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
