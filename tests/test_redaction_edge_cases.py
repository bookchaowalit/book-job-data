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


if __name__ == "__main__":
    unittest.main()
