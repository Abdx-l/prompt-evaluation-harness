import asyncio
from pathlib import Path
import tempfile
import unittest

from compare import compare
from evaluate import evaluate, score


class HarnessTests(unittest.TestCase):
    def test_scoring_caching_and_paired_comparison(self):
        cases = [{"id":"a","input":"hello","checks":[{"type":"contains","value":"hello"},{"type":"max_words","value":2}]},
                 {"id":"b","input":"json","checks":[{"type":"json_keys","value":["status"]}]}]
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            first = asyncio.run(evaluate(cases,"v1",cache,{"a":"Hello friend","b":"oops"}))
            self.assertEqual([r["passed"] for r in first], [True, False])
            second = asyncio.run(evaluate(cases,"v1",cache,{"a":"wrong","b":"wrong"}))
            self.assertTrue(all(r["cached"] for r in second))
            self.assertEqual(first[0]["response"], second[0]["response"])
            candidate = asyncio.run(evaluate(cases,"v2",cache,{"a":"hello","b":"{\"status\":\"ok\"}"}))
            self.assertEqual(compare(first,candidate,7,500)["candidate_wins"],1)
        self.assertFalse(score("not json", [{"type":"json_keys","value":["a"]}])[0]["passed"])


if __name__ == "__main__":
    unittest.main()

