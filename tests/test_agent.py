import os, tempfile, unittest
from concierge.agent import Concierge
KB = os.path.join(os.path.dirname(__file__), "..", "kb")

class T(unittest.TestCase):
    def setUp(self):
        self.c = Concierge(KB, os.path.join(tempfile.mkdtemp(), "j.jsonl"))
    def test_answer_with_source(self):
        r = self.c.answer(1, "Сколько стоит доставка?")
        self.assertEqual(r["type"], "answer"); self.assertIn("delivery.md", r["sources"][0])
    def test_unknown_escalates(self):
        self.assertEqual(self.c.answer(1, "Скидка для пенсионеров?")["type"], "ticket")
    def test_action_needs_confirmation_and_logged(self):
        r = self.c.answer(1, "Списали оплату дважды")
        tid = r["ticket"]["ticket"]
        self.assertIsNotNone(self.c.decide(tid, "op", True))
        self.assertIsNone(self.c.decide(tid, "op", True))
        self.assertEqual([e["event"] for e in self.c.journal.read()], ["question", "answer", "escalated", "approved"])
if __name__ == "__main__": unittest.main()
