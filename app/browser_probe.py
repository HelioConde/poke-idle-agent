"""Captura passiva com Playwright. Sem cliques, leitura de cookies ou credenciais."""
from __future__ import annotations
import argparse
import time
from datetime import datetime, timezone
from pathlib import Path

URLS = {
    "world": "https://poke.idleworld.online/",
    "io": "https://pokeidle.io/",
}

def main() -> int:
    parser = argparse.ArgumentParser(description="Observação passiva, sem ações de bot")
    parser.add_argument("--game", choices=URLS, required=True)
    parser.add_argument("--seconds", type=int, default=30)
    parser.add_argument("--interval", type=int, default=10)
    parser.add_argument("--out", type=Path, default=Path("captures"))
    parser.add_argument("--io-profile", type=Path, default=Path(".local-io-profile"))
    args = parser.parse_args()
    if not 1 <= args.seconds <= 300 or not 2 <= args.interval <= 60:
        parser.error("--seconds: 1–300; --interval: 2–60")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        parser.error("Instale Playwright: py -3 -m pip install playwright")
    args.out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        if args.game == "io":
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(args.io_profile.resolve()), headless=False,
                viewport={"width": 1280, "height": 900})
        else:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 900})
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(URLS[args.game], wait_until="domcontentloaded", timeout=30000)
            elapsed, seq = 0, 0
            while elapsed < args.seconds:
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                target = args.out / f"{args.game}-{timestamp}-{seq:03d}.png"
                page.screenshot(path=str(target), full_page=False)
                print(f"Captura local: {target}")
                seq += 1
                waiting = min(args.interval, args.seconds - elapsed)
                if waiting > 0:
                    time.sleep(waiting)
                elapsed += waiting
        finally:
            context.close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
