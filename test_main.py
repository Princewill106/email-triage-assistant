import json
import unittest

import main


class TriageTests(unittest.TestCase):
    def test_buckets(self):
        got = {e["from"]: main.classify(e)["bucket"] for e in json.load(open("sample_emails.json"))}
        self.assertEqual(got["mrs.ade@brightschools.ng"], "Act now")
        self.assertEqual(got["tunde@harbourtraders.ng"], "Reply today")
        self.assertEqual(got["security@paypa1-support.com"], "Ignore / report")
        self.assertIn(got["newsletter@techcabal.com"], ("Read later", "Ignore / report"))


if __name__ == "__main__":
    unittest.main()
