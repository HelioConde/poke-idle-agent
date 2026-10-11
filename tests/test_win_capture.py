"""Regras de seleção sem janela real nem acesso à conta do jogo."""
import unittest

from app.win_capture import TargetWindow, select_window, suitable_window


class BackgroundWindowTests(unittest.TestCase):
    def test_unfocused_window_eligible(self):
        # O seletor não depende do foco do Windows.
        window = TargetWindow(123, "PokeIdle", 1280, 800, False)
        self.assertTrue(suitable_window(window))
        self.assertEqual(select_window([window]), window)

    def test_minimized_ignored(self):
        window = TargetWindow(1, "PokeIdle", 1280, 800, True)
        self.assertFalse(suitable_window(window))
        self.assertIsNone(select_window([window]))

    def test_small_window_ignored(self):
        self.assertIsNone(select_window([
            TargetWindow(1, "PokeIdle", 100, 100, False)]))

    def test_largest_window_selected(self):
        options = [
            TargetWindow(1, "PokeIdle", 400, 400, False),
            TargetWindow(2, "PokeIdle", 1280, 720, False),
            TargetWindow(3, "PokeIdle", 1920, 1080, True),
        ]
        self.assertEqual(select_window(options).handle, 2)

    def test_blank_image_detection_when_pillow_installed(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow opcional")
        from app.win_capture import looks_blank
        self.assertTrue(looks_blank(Image.new("RGB", (150, 200), "black")))
        image = Image.new("RGB", (150, 200), "black")
        for x in range(0, 150, 2):
            for y in range(0, 200, 2):
                image.putpixel((x, y), (200, 60, 30))
        self.assertFalse(looks_blank(image))

    def test_uniform_non_black_image_is_blank(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow opcional")
        from app.win_capture import looks_blank
        self.assertTrue(looks_blank(Image.new("RGB", (150, 200), (20, 40, 60))))


if __name__ == "__main__":
    unittest.main()
