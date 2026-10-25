"""python -m concierge --demo — консольная имитация диалога без токенов и сети."""
import sys, tempfile, os
from .agent import Concierge

SCRIPT = ["Сколько стоит доставка?", "Как вернуть товар?", "С меня списали оплату дважды по заказу 1042", "Есть ли у вас скидка для пенсионеров?"]

def demo():
    path = os.path.join(tempfile.mkdtemp(), "journal.jsonl")
    c = Concierge(os.path.join(os.path.dirname(__file__), "..", "kb"), path)
    def show_ticket(t):
        print(f"[оператор] заявка #{t['ticket']}: {t['reason']}; предлагаю: {t['proposed_action']}  [✅ Подтвердить] [❌ Отклонить]")
        c.decide(t["ticket"], "operator-demo", True)
        print("[оператор] нажал ✅ → клиенту: «Сотрудник подтвердил действие.»")
    for q in SCRIPT:
        print(f"\n[клиент] {q}")
        r = c.answer("client-demo", q)
        if r["type"] == "answer":
            print(f"[бот] {r['text']}\n      источник: {', '.join(r['sources'])}")
            if "ticket" in r: show_ticket(r["ticket"])
        else:
            print("[бот] Не нашёл ответа в базе — передал сотруднику."); show_ticket(r)
    print("\n--- журнал ---")
    for rec in c.journal.read():
        print({k: v for k, v in rec.items() if k != "ts"})

if __name__ == "__main__":
    if "--demo" in sys.argv: demo()
    else: print("Использование: python -m concierge --demo  |  python -m concierge.bot")
