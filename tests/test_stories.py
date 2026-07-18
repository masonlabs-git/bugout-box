"""Storybook shelf: Gutenberg cleanup, passage splitting, title match."""
import unittest
from unittest import mock

from box import stories

FAKE = """The Project Gutenberg eBook of Test Tale
*** START OF THE PROJECT GUTENBERG EBOOK TEST TALE ***

Once upon a time there was a small brown rabbit who lived at the edge of
a quiet green wood, and every morning he hopped down to the river.

He liked to watch the water go by, because the water always knew where
it was going, and that seemed very wise for something so soft.

*** END OF THE PROJECT GUTENBERG EBOOK TEST TALE ***
"""


class PassagesTest(unittest.TestCase):
    def test_boilerplate_stripped_and_paragraphs_joined(self):
        with mock.patch.object(stories, "SHELF") as shelf:
            (shelf / "t.txt").read_text.return_value = FAKE
            stories._cache.clear()
            out = stories.passages("t.txt")
        self.assertEqual(len(out), 1)
        self.assertIn("small brown rabbit", out[0])
        self.assertNotIn("Project Gutenberg", out[0])
        stories._cache.clear()


class MatchTest(unittest.TestCase):
    def test_requires_read_or_book_word(self):
        self.assertIsNone(stories.match("peter rabbit is my friend"))

    def test_match_checks_shelf_existence(self):
        with mock.patch.object(stories, "SHELF") as shelf:
            (shelf / "peter-rabbit.txt").exists.return_value = True
            got = stories.match("can you read peter rabbit")
        self.assertEqual(got, ("The Tale of Peter Rabbit",
                               "peter-rabbit.txt"))


if __name__ == "__main__":
    unittest.main()
