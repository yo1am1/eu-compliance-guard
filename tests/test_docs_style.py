"""The README's look is a rule, not a habit: one image format, rounded corners, no dead links."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PAGES = [ROOT / "README.md", ROOT / "CONTRIBUTING.md", ROOT / "SECURITY.md", *sorted((ROOT / "docs").glob("*.md"))]


def links(text: str) -> list[tuple[bool, str]]:
    """(is an image, target) for each Markdown link, found without regular expressions."""
    found, at = [], 0
    while (at := text.find("](", at)) != -1:
        end = text.find(")", at)
        opening, depth = at, 0  # the "[" that this "]" closes; a badge nests "[![alt](image)](link)"
        while opening >= 0:
            depth += (text[opening] == "]") - (text[opening] == "[")
            if depth == 0:
                break
            opening -= 1
        if end == -1 or opening < 0:
            break
        found.append((text[opening - 1:opening] == "!", text[at + 2:end].split(" ")[0]))
        at = end
    return found


class DocsStyleTests(unittest.TestCase):
    def test_every_local_link_and_image_exists(self):
        missing = []
        for page in PAGES:
            for _, target in links(page.read_text(encoding="utf-8")):
                path = target.split("#")[0]
                if not path or "://" in target or target.startswith("mailto:"):
                    continue
                if not (page.parent / path).exists():
                    missing.append(f"{page.relative_to(ROOT)} -> {target}")
        self.assertEqual(missing, [])

    def test_every_local_image_is_a_rounded_webp_or_the_diagram(self):
        """Screenshots are WebP with an alpha channel (the rounded corners baked in by
        scripts/readme_images.py); the only other image is an SVG. No PNG, JPEG or GIF."""
        seen = set()
        for page in PAGES:
            for image, target in links(page.read_text(encoding="utf-8")):
                if image and "://" not in target:
                    seen.add((page.parent / target).resolve())
        self.assertTrue(seen)
        for path in sorted(seen):
            with self.subTest(image=path.name):
                self.assertIn(path.suffix, (".webp", ".svg"))
                if path.suffix == ".webp":
                    header = path.read_bytes()[:32]
                    self.assertEqual((header[:4], header[8:16]), (b"RIFF", b"WEBPVP8X"))  # the extended format
                    self.assertTrue(header[20] & 0x10, "no alpha channel: corners are not rounded")
        on_disk = {path.resolve() for path in (ROOT / "docs/images").iterdir()}
        self.assertEqual(on_disk - seen, set(), "an image nothing shows")

    def test_images_have_alt_text(self):
        for page in PAGES:
            text = page.read_text(encoding="utf-8")
            self.assertNotIn("![](", text, page.name)

    def test_the_diagram_sets_the_corner_radius_the_images_follow(self):
        diagram = (ROOT / "docs/architecture.svg").read_text(encoding="utf-8")
        self.assertIn('width="1200"', diagram)
        self.assertIn('<rect x="0" y="0" width="1200" height="880" rx="18"', diagram)
        script = (ROOT / "scripts/readme_images.py").read_text(encoding="utf-8")
        self.assertIn("RADIUS_SHARE = 18 / 1200", script)

    def test_the_citation_file_names_the_released_version(self):
        from eu_compliance_guard import __version__
        self.assertIn(f"\nversion: {__version__}\n", (ROOT / "CITATION.cff").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
