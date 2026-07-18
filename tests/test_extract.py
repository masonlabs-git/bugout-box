import unittest

from box.extract import _first_json, parse_supply


class SupplyParseTest(unittest.TestCase):
    def test_received(self):
        r = parse_supply("we received 40 blankets")
        self.assertEqual(r, {"item": "blankets", "delta": 40.0, "unit": ""})

    def test_distributed_with_unit(self):
        r = parse_supply("distributed 12 cases of water")
        self.assertEqual(r["item"], "water")
        self.assertEqual(r["delta"], -12.0)
        self.assertEqual(r["unit"], "cases")

    def test_gave_is_negative(self):
        r = parse_supply("gave out 5 bottles of bleach")
        self.assertEqual(r["delta"], -5.0)
        self.assertEqual(r["item"], "bleach")

    def test_no_match(self):
        self.assertIsNone(parse_supply("how is everyone doing"))

    def test_decimal_quantity(self):
        r = parse_supply("received 2.5 gallons of fuel")
        self.assertEqual(r["delta"], 2.5)
        self.assertEqual(r["unit"], "gallons")


class JsonExtractTest(unittest.TestCase):
    def test_pulls_json_from_chatter(self):
        raw = 'Sure! {"names":"Ana","medical":"","missing":"","phone":""} ok'
        self.assertEqual(_first_json(raw)["names"], "Ana")

    def test_bad_json_returns_none(self):
        self.assertIsNone(_first_json("no json here"))


if __name__ == "__main__":
    unittest.main()
