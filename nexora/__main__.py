"""Run Nexora: python -m nexora"""

from __future__ import annotations

import argparse
import socket
import sys
import threading
import time
import webbrowser

import uvicorn


def _free_port(preferred: int = 8765) -> int:
    for port in range(preferred, preferred + 40):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return preferred


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Nexora — включение и отключение интернета")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0, help="0 = автовыбор")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)

    port = args.port or _free_port()
    url = f"http://{args.host}:{port}"

    if not args.no_browser:
        def open_browser() -> None:
            time.sleep(0.6)
            webbrowser.open(url)

        threading.Thread(target=open_browser, daemon=True).start()

    print(f"Nexora: {url}")
    print("Для управления сетью обычно нужны права администратора / sudo.")
    uvicorn.run("nexora.app:app", host=args.host, port=port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
