"""Логика агента, не зависящая от Telegram: ответ по базе, эскалация, подтверждение."""
import itertools, os, re
from .rag import KnowledgeBase
from .journal import Journal

ACTION_WORDS = re.compile(r"верн|возврат|отмен|дважды|списал|заказ\s*№?\s*\d+", re.I)

class Concierge:
    def __init__(self, kb_dir, journal_path, llm=None):
        self.kb = KnowledgeBase(kb_dir)
        self.journal = Journal(journal_path)
        self.llm = llm  # callable(question, context) -> str или None (тогда — цитата из базы)
        self.pending = {}
        self._ids = itertools.count(1)

    def answer(self, user_id, question):
        self.journal.write("question", user=user_id, text=question)
        hits = self.kb.search(question)
        if not hits:
            return self.escalate(user_id, question, reason="нет ответа в базе")
        context = "\n".join(h.text for h in hits)
        text = self.llm(question, context) if self.llm else hits[0].text
        sources = [h.source for h in hits]
        self.journal.write("answer", user=user_id, sources=sources)
        reply = {"type": "answer", "text": text, "sources": sources}
        if ACTION_WORDS.search(question):
            reply["ticket"] = self.escalate(user_id, question, reason="нужно действие сотрудника")
        return reply

    def escalate(self, user_id, question, reason):
        tid = next(self._ids)
        self.pending[tid] = {"user": user_id, "question": question, "reason": reason}
        self.journal.write("escalated", ticket=tid, user=user_id, reason=reason)
        return {"type": "ticket", "ticket": tid, "reason": reason,
                "proposed_action": "оформить возврат/проверку платежа" if ACTION_WORDS.search(question) else "ответить вручную"}

    def decide(self, ticket_id, operator, approved):
        t = self.pending.pop(ticket_id, None)
        if t is None:
            return None
        self.journal.write("approved" if approved else "rejected", ticket=ticket_id, operator=operator)
        return t

def make_llm():
    """Необязательно: OpenAI-совместимый API (GigaChat/Groq/OpenRouter и т.п.) из .env."""
    url, key, model = os.getenv("LLM_BASE_URL"), os.getenv("LLM_API_KEY"), os.getenv("LLM_MODEL")
    if not (url and key and model):
        return None
    import json, urllib.request
    def call(q, ctx):
        body = json.dumps({"model": model, "messages": [
            {"role": "system", "content": "Отвечай только по контексту. Если ответа нет — скажи, что передашь сотруднику.\n" + ctx},
            {"role": "user", "content": q}]}).encode()
        req = urllib.request.Request(url.rstrip("/") + "/chat/completions", body,
                                     {"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)["choices"][0]["message"]["content"]
        except Exception:
            return ctx.split("\n")[0]  # откат: цитата из базы
    return call
