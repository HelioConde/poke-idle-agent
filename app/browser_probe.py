"""Captura passiva: navegador NORMAL no Windows; sem acesso a cookies nem login."""
from __future__ import annotations

import argparse
import sys
import time
import unicodedata
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

URLS = {"world": "https://poke.idleworld.online/", "io": "https://pokeidle.io/"}


def normalize_title(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", value.lower())
                   if not unicodedata.combining(c))


def title_matches_game(title: str, game: str) -> bool:
    title = normalize_title(title)
    if game == "io":
        if "idleworld" in title or "idle world" in title:
            return False
        return any(s in title for s in ("pokeidle", "poke idle io", "poke idle - io"))
    if game == "world":
        return any(s in title for s in ("idleworld", "poke idle world", "pokeidle world"))
    return False


def active_game_window(game: str) -> tuple[int, int, int, int] | None:
    """Retorna coordenadas da janela ativa somente se pertencer ao jogo."""
    if sys.platform != "win32":
        raise RuntimeError("Modo desktop funciona no Windows.")
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowTextLengthW.argtypes = (wintypes.HWND,)
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.GetClassNameW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
    user32.GetClassNameW.restype = ctypes.c_int
    user32.GetWindowRect.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.RECT))
    user32.GetWindowRect.restype = wintypes.BOOL

    handle = user32.GetForegroundWindow()
    if not handle:
        return None
    class_name = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(handle, class_name, len(class_name))
    # Chrome/Edge comuns e Firefox. Nunca conectar ao navegador por automação.
    if not any(m in class_name.value.lower() for m in
               ("chrome_widgetwin", "mozillawindowclass")):
        return None
    length = user32.GetWindowTextLengthW(handle)
    title = ctypes.create_unicode_buffer(min(4096, length + 1))
    user32.GetWindowTextW(handle, title, len(title))
    if not title_matches_game(title.value, game):
        return None
    rect = wintypes.RECT()
    if not user32.GetWindowRect(handle, ctypes.byref(rect)):
        return None
    if rect.right <= rect.left or rect.bottom <= rect.top:
        return None
    return rect.left, rect.top, rect.right, rect.bottom


def capture_desktop(game: str, seconds: int, interval: int,
                    out: Path, top_crop: int, open_browser: bool) -> int:
    if sys.platform != "win32":
        raise RuntimeError("Modo desktop requer Windows.")
    try:
        from PIL import ImageGrab
    except ImportError as exc:
        raise RuntimeError(
            "Instale Pillow: py -3 -m pip install -r requirements-desktop.txt"
        ) from exc

    # Coordenadas consistentes com DPI/escala de vídeo em muitos PCs Windows.
    import ctypes
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except (AttributeError, OSError):
        pass
    if open_browser:
        webbrowser.open(URLS[game], new=2)

    print("Abra o jogo no Chrome/Edge NORMAL e faça login pelo Google se precisar.")
    print("A captura NÃO controla o navegador nem lê senhas ou cookies.")
    print("Telas Google e outras abas serão ignoradas.")
    try:
        input("Com o JOGO aberto, pressione ENTER no terminal...")
    except EOFError as exc:
        raise RuntimeError("Inicie em um terminal interativo.") from exc
    print("Clique na janela do jogo em até 4 segundos.")
    time.sleep(4)
    out.mkdir(parents=True, exist_ok=True)

    end_time = time.monotonic() + seconds
    saved = 0
    skipped = 0
    while True:
        rect = active_game_window(game)
        if rect is None:
            skipped += 1
            print("Aguardando foco na janela do jogo; nenhuma captura salva.")
        else:
            left, top, right, bottom = rect
            top += top_crop  # Exclui barra de endereço e abas.
            if right - left >= 200 and bottom - top >= 150:
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                filename = out / f"{game}-{stamp}-{saved:03d}.png"
                ImageGrab.grab(bbox=(left, top, right, bottom),
                               all_screens=True).save(filename)
                print(f"Captura local: {filename}")
                saved += 1
            else:
                skipped += 1
                print("Janela pequena demais: captura ignorada.")
        remaining = end_time - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(interval, remaining))

    print(f"Concluído: {saved} capturas, {skipped} ciclos ignorados.")
    if saved == 0:
        print("Deixe a aba do jogo ativa no Chrome/Edge comum, fora da tela Google.")
        return 2
    print("Mantenha capturas privadas fora do repositório GitHub.")
    return 0



def capture_background_window(game: str, seconds: int, interval: int,
                              out: Path, top_crop: int,
                              open_browser: bool) -> int:
    """Captura a janela do jogo mesmo quando OUTRO programa tem o foco."""
    if sys.platform != "win32":
        raise RuntimeError("Modo window requer Windows.")

    from app.win_capture import capture_window, find_windows, looks_blank, select_window

    try:
        from PIL import Image  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "Instale Pillow: py -3 -m pip install -r requirements-desktop.txt"
        ) from exc

    if open_browser:
        webbrowser.open(URLS[game], new=1)

    print("Abra o Poke Idle no Chrome normal, em uma JANELA SEPARADA.")
    print("Faça login manualmente e deixe a aba do jogo selecionada nessa janela.")
    print("Depois pode usar outro programa na frente: o Chrome NAO precisa ter foco.")
    print("Nao minimize o Chrome. Windows pode deixar de renderizar janelas minimizadas.")
    try:
        input("Pressione ENTER quando a janela do jogo estiver carregada...")
    except EOFError as exc:
        raise RuntimeError("Inicie em um terminal interativo.") from exc

    out.mkdir(parents=True, exist_ok=True)
    end_time = time.monotonic() + seconds
    saved, skipped, consecutive_same = 0, 0, 0
    last_sample: bytes | None = None
    while True:
        candidates = find_windows(game)
        target = select_window(candidates)
        if target is None:
            skipped += 1
            if any(item.minimized for item in candidates):
                print("Janela encontrada, mas MINIMIZADA. Restaure sem dar foco.")
            else:
                print("Nao encontrei janela com a aba do jogo selecionada. "
                      "Use uma janela Chrome separada para o jogo.")
        else:
            try:
                screenshot = capture_window(target, top_crop)
                if looks_blank(screenshot):
                    skipped += 1
                    print("Captura em branco ou uniforme. O Chrome/GPU pode "
                          "nao aceitar PrintWindow; nenhuma imagem salva.")
                else:
                    sample = screenshot.resize((64, 36)).tobytes()
                    consecutive_same = consecutive_same + 1 if sample == last_sample else 0
                    last_sample = sample
                    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                    path = out / f"{game}-background-{stamp}-{saved:03d}.png"
                    screenshot.save(path)
                    print(f"Captura em segundo plano: {path}")
                    saved += 1
                    if consecutive_same >= 2:
                        print("Atencao: 3+ capturas identicas. Pode ser "
                              "uma tela estatica ou o Chrome parou de atualizar.")
            except (OSError, ValueError) as exc:
                skipped += 1
                print(f"Falha ao capturar janela em segundo plano: {exc}")

        remaining = end_time - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(interval, remaining))

    print(f"Concluido: {saved} imagens salvas, {skipped} tentativas ignoradas.")
    if saved == 0:
        print("Sem frames validos. A captura PrintWindow varia por Chrome/GPU.")
        print("Uma alternativa futura e captura de janela via Windows Graphics Capture/OBS.")
        return 2
    return 0


def capture_public_playwright(game: str, seconds: int, interval: int, out: Path) -> int:
    """Playwright exclusivamente para a landing pública; sem autenticação."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Instale Playwright: py -3 -m pip install -r requirements-browser.txt"
        ) from exc
    print("Playwright: apenas páginas PÚBLICAS; não tente autenticar o Google aqui.")
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(URLS[game], wait_until="domcontentloaded", timeout=30000)
            deadline = time.monotonic() + seconds
            sequence = 0
            while True:
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                path = out / f"{game}-public-{stamp}-{sequence:03d}.png"
                page.screenshot(path=str(path), full_page=False)
                print(f"Captura pública: {path}")
                sequence += 1
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                time.sleep(min(interval, remaining))
        finally:
            browser.close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Captura passiva de jogos")
    parser.add_argument("--game", choices=URLS, required=True)
    parser.add_argument("--mode", choices=("window", "desktop", "playwright"), default="window",
                        help="window = captura de janela fora de foco (padrão); desktop = apenas foco; playwright = página pública")
    parser.add_argument("--seconds", type=int, default=30)
    parser.add_argument("--interval", type=int, default=10)
    parser.add_argument("--out", type=Path, default=Path("captures"))
    parser.add_argument("--top-crop", type=int, default=105,
                        help="Oculta barra de endereço/abas (80–300 pixels)")
    parser.add_argument("--open-browser", action="store_true",
                        help="Abre a URL no navegador padrão do Windows")
    args = parser.parse_args()
    if not 1 <= args.seconds <= 300 or not 2 <= args.interval <= 60:
        parser.error("--seconds: 1..300; --interval: 2..60")
    if not 80 <= args.top_crop <= 300:
        parser.error("--top-crop: 80..300 (não pode capturar barra de URL)")
    try:
        if args.mode == "window":
            return capture_background_window(args.game, args.seconds, args.interval,
                                             args.out, args.top_crop, args.open_browser)
        if args.mode == "desktop":
            return capture_desktop(args.game, args.seconds, args.interval, args.out,
                                   args.top_crop, args.open_browser)
        return capture_public_playwright(args.game, args.seconds, args.interval, args.out)
    except (RuntimeError, OSError) as exc:
        parser.exit(1, f"Erro: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
