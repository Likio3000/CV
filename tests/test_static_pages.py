from __future__ import annotations

import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGES = ("index.html", "portfolio.html", "work-logs.html")


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.main_ids: list[str | None] = []
        self.links: list[dict[str, str | None]] = []
        self.h1_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "main":
            self.main_ids.append(attributes.get("id"))
        elif tag == "a":
            self.links.append(attributes)
        elif tag == "h1":
            self.h1_count += 1


class StaticPageAccessibilityTests(unittest.TestCase):
    def parse_page(self, filename: str) -> PageParser:
        parser = PageParser()
        parser.feed((ROOT / filename).read_text(encoding="utf-8"))
        return parser

    def test_every_page_has_one_main_target_and_skip_link(self) -> None:
        for filename in PAGES:
            with self.subTest(filename=filename):
                page = self.parse_page(filename)
                self.assertEqual(page.main_ids, ["main-content"])
                self.assertTrue(
                    any(link.get("href") == "#main-content" for link in page.links)
                )

    def test_every_page_has_one_current_navigation_link(self) -> None:
        for filename in PAGES:
            with self.subTest(filename=filename):
                page = self.parse_page(filename)
                current_links = [
                    link for link in page.links if link.get("aria-current") == "page"
                ]
                self.assertEqual(len(current_links), 1)

    def test_every_page_has_a_primary_heading(self) -> None:
        for filename in PAGES:
            with self.subTest(filename=filename):
                self.assertEqual(self.parse_page(filename).h1_count, 1)

    def test_new_tab_links_are_protected(self) -> None:
        for filename in PAGES:
            with self.subTest(filename=filename):
                for link in self.parse_page(filename).links:
                    if link.get("target") != "_blank":
                        continue
                    self.assertIn("noopener", (link.get("rel") or "").split())


if __name__ == "__main__":
    unittest.main()
