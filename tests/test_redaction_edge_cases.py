"""Contact redaction must survive Thai text and HTML-sourced Unicode spacing."""
import unittest

from book_job_data.privacy import EMAIL_MASK, PHONE_MASK, redact_text


class RedactionEdgeCaseTests(unittest.TestCase):
    def test_phone_glued_to_thai_words_is_masked(self):
        # Thai writes words without spaces: "โทร" = "call", "ค่ะ" = polite particle.
        for text in ("โทร081-234-5678", "โทร.0812345678", "ติดต่อ0812345678ค่ะ", "Tel.0812345678"):
            with self.subTest(text=text):
                self.assertIn(PHONE_MASK, redact_text(text))
                self.assertNotIn("5678", redact_text(text))

    def test_unicode_spaces_and_dashes_between_groups(self):
        for sep in (" ", " ", " ", "‑", "–", "−"):
            text = f"call 081{sep}234{sep}5678"
            with self.subTest(sep=hex(ord(sep))):
                self.assertEqual(redact_text(text), f"call {PHONE_MASK}")

    def test_invisible_characters_do_not_hide_contacts(self):
        self.assertEqual(redact_text("mail hr​@acme.io"), f"mail {EMAIL_MASK}")
        self.assertEqual(redact_text("call 081­234⁠5678"), f"call {PHONE_MASK}")

    def test_non_contacts_still_survive(self):
        for text in ("120000 - 170000 THB", "posted 2026-09-30", "https://x.io/jobs/123456789012", "v1.2.3"):
            with self.subTest(text=text):
                self.assertEqual(redact_text(text), text)

    def test_glued_salary_ranges_are_not_phones(self):
        for text in (
            "30000-50000",
            "30,000-50,000",
            "\u0e3f30000-\u0e3f50000",
            "25000\u201335000 THB",
            "\u0e40\u0e07\u0e34\u0e19\u0e40\u0e14\u0e37\u0e2d\u0e19120000-170000\u0e1a\u0e32\u0e17",
        ):
            with self.subTest(text=text):
                self.assertEqual(redact_text(text), text)

    def test_two_group_phones_still_masked(self):
        for text in ("081-2345678", "02-1234567", "1800-123456", "+66-812345678"):
            with self.subTest(text=text):
                self.assertEqual(redact_text(text), PHONE_MASK)

    def test_range_lookalike_phones_are_masked(self):
        # "6681-2345678" is +66 81 234 5678 without the "+"; the others have
        # mismatched amount lengths, so they cannot be a salary range.
        for text in ("6681-2345678", "1234-567890", "10000-2000000", "66812-345678"):
            with self.subTest(text=text):
                self.assertEqual(redact_text(text), PHONE_MASK)

    def test_salary_range_starting_1800_digits_survives(self):
        self.assertEqual(redact_text("18000-25000"), "18000-25000")


if __name__ == "__main__":
    unittest.main()
