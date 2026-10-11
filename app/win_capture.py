"""Captura de janela Win32 fora de foco.

O método PrintWindow tenta desenhar a janela selecionada mesmo quando ela
não está em primeiro plano, sem usar automação nem ler cookies do Chrome.
Chrome/GPU pode devolver imagem preta ou imagem congelada; minimizar costuma
impedir a captura. Não é uma garantia de fluxo de frames atualizado.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image


@dataclass(frozen=True)
class TargetWindow:
    handle: int
    title: str
    width: int
    height: int
    minimized: bool


def suitable_window(target: TargetWindow) -> bool:
    return (not target.minimized and target.width >= 200 and
            target.height >= 150)


def looks_blank(image: "Image.Image") -> bool:
    """Detecta imagem quase uniforme (PrintWindow devolveu frame vazio).

    A checagem precisa usar a imagem original: reduzir um padrão regular de
    pixels pode transformá-lo artificialmente em um cinza uniforme e fazer
    uma captura válida parecer vazia.
    """
    rgb = image.convert("RGB")
    extrema = rgb.getextrema()
    return all((high - low) < 3 for low, high in extrema)


def find_windows(game: str) -> list[TargetWindow]:
    """Procura janela Chrome/Edge/Firefox cuja ABA ATUAL é o jogo solicitado."""
    if sys.platform != "win32":
        raise RuntimeError("Captura de janela requer Windows.")

    import ctypes
    from ctypes import wintypes

    from app.browser_probe import title_matches_game

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.EnumWindows.argtypes = [
        ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM),
        wintypes.LPARAM,
    ]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.GetClassNameW.argtypes = [
        wintypes.HWND, wintypes.LPWSTR, ctypes.c_int
    ]
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [
        wintypes.HWND, wintypes.LPWSTR, ctypes.c_int
    ]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.IsIconic.restype = wintypes.BOOL
    user32.GetWindowRect.argtypes = [
        wintypes.HWND, ctypes.POINTER(wintypes.RECT)
    ]
    user32.GetWindowRect.restype = wintypes.BOOL

    windows: list[TargetWindow] = []
    CALLBACK = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def collect(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True

        class_name = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_name, len(class_name))
        if not any(text in class_name.value.lower() for text in
                   ("chrome_widgetwin", "mozillawindowclass")):
            return True

        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        title = ctypes.create_unicode_buffer(min(length + 1, 4096))
        user32.GetWindowTextW(hwnd, title, len(title))
        if not title_matches_game(title.value, game):
            return True

        rect = wintypes.RECT()
        if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            windows.append(TargetWindow(
                int(hwnd), title.value, rect.right - rect.left,
                rect.bottom - rect.top, bool(user32.IsIconic(hwnd))
            ))
        return True

    callback = CALLBACK(collect)
    if not user32.EnumWindows(callback, 0):
        raise OSError("EnumWindows falhou ao localizar janelas.")
    return windows


def select_window(windows: list[TargetWindow]) -> TargetWindow | None:
    """Maior janela elegível; sempre ignora janelas minimizadas."""
    eligible = [window for window in windows if suitable_window(window)]
    return max(eligible, key=lambda w: w.width * w.height, default=None)


def capture_window(target: TargetWindow, top_crop: int) -> "Image.Image":
    """Win32 PrintWindow com buffer offscreen 32-bit; nunca captura tela inteira."""
    if sys.platform != "win32":
        raise RuntimeError("Captura de janela requer Windows.")
    if not suitable_window(target):
        raise ValueError("Janela minimizada ou pequena demais.")

    import ctypes
    from ctypes import wintypes
    from PIL import Image

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD),
            ("biWidth", wintypes.LONG),
            ("biHeight", wintypes.LONG),
            ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD),
            ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD),
            ("biXPelsPerMeter", wintypes.LONG),
            ("biYPelsPerMeter", wintypes.LONG),
            ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        ]

    class BITMAPINFO(ctypes.Structure):
        _fields_ = [("bmiHeader", BITMAPINFOHEADER),
                    ("bmiColors", wintypes.DWORD * 3)]

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

    user32.GetWindowDC.argtypes = [wintypes.HWND]
    user32.GetWindowDC.restype = wintypes.HDC
    user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    user32.ReleaseDC.restype = ctypes.c_int
    user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
    user32.PrintWindow.restype = wintypes.BOOL

    gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi32.CreateCompatibleDC.restype = wintypes.HDC
    gdi32.CreateDIBSection.argtypes = [
        wintypes.HDC, ctypes.POINTER(BITMAPINFO), wintypes.UINT,
        ctypes.POINTER(ctypes.c_void_p), wintypes.HANDLE, wintypes.DWORD
    ]
    gdi32.CreateDIBSection.restype = wintypes.HBITMAP
    gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
    gdi32.SelectObject.restype = wintypes.HGDIOBJ
    gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    gdi32.DeleteObject.restype = wintypes.BOOL
    gdi32.DeleteDC.argtypes = [wintypes.HDC]
    gdi32.DeleteDC.restype = wintypes.BOOL

    hwnd = wintypes.HWND(target.handle)
    window_dc = user32.GetWindowDC(hwnd)
    if not window_dc:
        raise OSError("GetWindowDC falhou.")

    buffer_dc = None
    bitmap = None
    previous = None
    try:
        buffer_dc = gdi32.CreateCompatibleDC(window_dc)
        if not buffer_dc:
            raise OSError("CreateCompatibleDC falhou.")
        width, height = target.width, target.height
        if width > 8192 or height > 8192:
            raise ValueError("Janela maior que o limite de captura.")

        info = BITMAPINFO()
        info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        info.bmiHeader.biWidth = width
        info.bmiHeader.biHeight = -height  # imagem de cima para baixo
        info.bmiHeader.biPlanes = 1
        info.bmiHeader.biBitCount = 32
        info.bmiHeader.biCompression = 0  # BI_RGB
        ptr = ctypes.c_void_p()
        bitmap = gdi32.CreateDIBSection(
            window_dc, ctypes.byref(info), 0, ctypes.byref(ptr), None, 0
        )
        if not bitmap or not ptr.value:
            raise OSError("CreateDIBSection falhou.")
        previous = gdi32.SelectObject(buffer_dc, bitmap)
        if not previous:
            raise OSError("SelectObject falhou.")

        # PW_RENDERFULLCONTENT=2: captura janela parcialmente/totalmente oculta
        # Pode falhar em algumas versões/implementações de Chrome/GPU.
        if not user32.PrintWindow(hwnd, buffer_dc, 2):
            raise OSError("PrintWindow recusou a captura.")
        raw = ctypes.string_at(ptr, width * height * 4)
        image = Image.frombytes("RGB", (width, height), raw, "raw", "BGRX")
        if height - top_crop < 150:
            raise ValueError("Corte da barra superior é grande demais.")
        return image.crop((0, top_crop, width, height))
    finally:
        if previous and buffer_dc:
            gdi32.SelectObject(buffer_dc, previous)
        if bitmap:
            gdi32.DeleteObject(bitmap)
        if buffer_dc:
            gdi32.DeleteDC(buffer_dc)
        user32.ReleaseDC(hwnd, window_dc)
