"""Interfaz web local (solo escucha en 127.0.0.1)."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import uuid
import webbrowser
from collections import deque
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from .core import FORMATS, DownloadOptions, check_ffmpeg, default_output_dir, download

app = Flask(__name__)
_jobs: dict[str, dict] = {}
_queue: deque[str] = deque()
_lock = threading.Lock()
_wake = threading.Event()


def _worker() -> None:
    while True:
        _wake.wait()
        with _lock:
            job_id = _queue.popleft() if _queue else None
            if not _queue:
                _wake.clear()
        if job_id is None:
            continue
        job = _jobs[job_id]
        job["status"] = "running"

        def hook(d: dict, job=job) -> None:
            info = d.get("info_dict") or {}
            title = info.get("title") or Path(d.get("filename", "")).name
            if d.get("status") == "downloading":
                job["current"] = title
                job["percent"] = d.get("_percent_str", "").strip()
            elif d.get("status") == "finished" and d.get("postprocessor") == "MoveFiles":
                job["done"].append(title)

        try:
            code = download(job["opts"], hook)
            job["status"] = "done" if code == 0 else "done_with_errors"
        except Exception as e:  # noqa: BLE001 - mostramos el error en la UI
            job["status"] = "error"
            job["error"] = str(e)
        job["current"] = None


@app.get("/")
def index():
    return render_template("index.html", formats=FORMATS, ffmpeg=check_ffmpeg(), default_out=str(default_output_dir()))


@app.post("/api/jobs")
def create_job():
    data = request.get_json(force=True)
    urls = [u.strip() for u in data.get("urls", "").splitlines() if u.strip()]
    if not urls:
        return jsonify(error="Pega al menos una URL"), 400
    opts = DownloadOptions(
        urls=urls,
        output_dir=Path(data.get("output") or default_output_dir()),
        audio_format=data.get("format", "flac"),
        sample_rate=int(data["sample_rate"]) if data.get("sample_rate") else None,
        normalize=bool(data.get("normalize")),
        playlist_items=data.get("items") or None,
    )
    job_id = uuid.uuid4().hex[:8]
    _jobs[job_id] = {
        "id": job_id, "urls": urls, "format": opts.audio_format,
        "output": str(opts.output_dir.expanduser().resolve()),
        "status": "queued", "current": None, "percent": "", "done": [], "error": None, "opts": opts,
    }
    with _lock:
        _queue.append(job_id)
        _wake.set()
    return jsonify(id=job_id)


@app.post("/api/open")
def open_folder():
    path = Path(request.get_json(force=True).get("path") or default_output_dir()).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(path)])
    return jsonify(ok=True)


@app.get("/api/jobs")
def list_jobs():
    return jsonify([{k: v for k, v in j.items() if k != "opts"} for j in reversed(_jobs.values())])


def run(port: int = 5055) -> None:
    threading.Thread(target=_worker, daemon=True).start()
    url = f"http://127.0.0.1:{port}"
    print(f"Loseless corriendo en {url}  (Ctrl+C para salir)")
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=port, debug=False)
