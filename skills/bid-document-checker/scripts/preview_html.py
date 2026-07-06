#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Publish one HTML report through a temporary Cloudflare Tunnel.

This helper deliberately exposes a copied single-file preview directory, not the
original project, skill, or report folder.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path


DEFAULT_STATE = Path(tempfile.gettempdir()) / "bid-html-preview-current.json"
DEFAULT_TMP_ROOT = Path(tempfile.gettempdir()) / "bid-html-preview"
URL_RE = re.compile(r"https://[-a-zA-Z0-9]+\.trycloudflare\.com")


def find_cloudflared() -> str:
    candidates = [
        shutil.which("cloudflared"),
        "/opt/homebrew/bin/cloudflared",
        "/usr/local/bin/cloudflared",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    raise SystemExit(
        "ERROR: cloudflared not found. Install it first, for example: brew install cloudflared"
    )


def pick_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def kill_process_group(pid: int) -> None:
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except PermissionError:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            return


def stop_preview(state_path: Path, keep_state: bool = False) -> int:
    if not state_path.exists():
        print(f"No preview state found: {state_path}")
        return 0

    state = json.loads(state_path.read_text(encoding="utf-8"))
    for key in ("cloudflared_pid", "server_pid"):
        pid = state.get(key)
        if isinstance(pid, int):
            kill_process_group(pid)

    if not keep_state:
        try:
            state_path.unlink()
        except FileNotFoundError:
            pass

    print("Stopped preview.")
    print(f"preview_url: {state.get('preview_url', '-')}")
    print(f"preview_dir: {state.get('preview_dir', '-')}")
    return 0


def wait_for_url(log_path: Path, timeout: int) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if log_path.exists():
            text = log_path.read_text(encoding="utf-8", errors="ignore")
            match = URL_RE.search(text)
            if match:
                return match.group(0)
        time.sleep(0.5)
    raise TimeoutError(f"Timed out waiting for Cloudflare URL. See log: {log_path}")


def publish(args: argparse.Namespace) -> int:
    html_path = Path(args.html).expanduser().resolve()
    if not html_path.exists():
        raise SystemExit(f"ERROR: HTML file not found: {html_path}")
    if html_path.suffix.lower() not in {".html", ".htm"}:
        raise SystemExit(f"ERROR: only .html/.htm files can be previewed: {html_path}")

    state_path = Path(args.state).expanduser().resolve()
    if state_path.exists() and not args.keep_existing:
        stop_preview(state_path)

    cloudflared = find_cloudflared()
    tmp_root = Path(args.tmp_root).expanduser().resolve()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    preview_dir = tmp_root / f"preview-{timestamp}-{uuid.uuid4().hex[:8]}"
    preview_dir.mkdir(parents=True, exist_ok=False)

    copied_html = preview_dir / "index.html"
    shutil.copy2(html_path, copied_html)

    port = int(args.port) if args.port else pick_port()
    server_log = preview_dir / "http-server.log"
    tunnel_log = preview_dir / "cloudflared.log"

    server_log_handle = server_log.open("w", encoding="utf-8")
    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "http.server",
            str(port),
            "--bind",
            "127.0.0.1",
            "--directory",
            str(preview_dir),
        ],
        stdout=server_log_handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

    time.sleep(0.8)
    if server.poll() is not None:
        server_log_handle.close()
        raise SystemExit(f"ERROR: HTTP server failed. See log: {server_log}")

    tunnel_log_handle = tunnel_log.open("w", encoding="utf-8")
    tunnel = subprocess.Popen(
        [cloudflared, "tunnel", "--url", f"http://127.0.0.1:{port}"],
        stdout=tunnel_log_handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

    try:
        preview_url = wait_for_url(tunnel_log, int(args.timeout))
    except Exception:
        kill_process_group(tunnel.pid)
        kill_process_group(server.pid)
        tunnel_log_handle.close()
        server_log_handle.close()
        raise

    state = {
        "preview_url": preview_url,
        "source_html": str(html_path),
        "copied_html": str(copied_html),
        "preview_dir": str(preview_dir),
        "local_url": f"http://127.0.0.1:{port}/",
        "port": port,
        "server_pid": server.pid,
        "cloudflared_pid": tunnel.pid,
        "server_log": str(server_log),
        "cloudflared_log": str(tunnel_log),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    print("preview_status: running")
    print(f"preview_url: {preview_url}")
    print(f"source_html: {html_path}")
    print(f"copied_html: {copied_html}")
    print(f"state_file: {state_path}")
    print(f"stop_command: python3 {Path(__file__).resolve()} --stop --state {state_path}")
    print("warning: anyone with the URL can view this copied HTML while the tunnel is running.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Publish one HTML report through a temporary Cloudflare Tunnel."
    )
    parser.add_argument("--html", help="HTML report path to publish as a single-file preview")
    parser.add_argument("--port", type=int, default=0, help="Local port; default is auto")
    parser.add_argument("--tmp-root", default=str(DEFAULT_TMP_ROOT), help="Temporary preview root")
    parser.add_argument("--state", default=str(DEFAULT_STATE), help="State JSON path")
    parser.add_argument("--timeout", type=int, default=45, help="Seconds to wait for tunnel URL")
    parser.add_argument("--stop", action="store_true", help="Stop the preview recorded in --state")
    parser.add_argument("--keep-state", action="store_true", help="Do not remove state file on stop")
    parser.add_argument("--keep-existing", action="store_true", help="Do not stop an existing preview state before publishing")
    args = parser.parse_args()

    if args.stop:
        return stop_preview(Path(args.state).expanduser().resolve(), keep_state=args.keep_state)
    if not args.html:
        parser.error("--html is required unless --stop is used")
    return publish(args)


if __name__ == "__main__":
    sys.exit(main())
