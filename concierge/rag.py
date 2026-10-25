"""Простой RAG без внешних зависимостей: чанки по абзацам markdown + BM25."""
import math, re
from dataclasses import dataclass
from pathlib import Path

TOKEN = re.compile(r"[a-zа-яё0-9]+", re.I)

def tokens(text):
    # грубый стемминг: обрезаем до 5 символов, чтобы «возврат/возвращается» совпадали
    return [t.lower()[:5] for t in TOKEN.findall(text) if len(t) > 2]

@dataclass
class Chunk:
    source: str
    title: str
    text: str

class KnowledgeBase:
    def __init__(self, folder):
        self.chunks = []
        for path in sorted(Path(folder).glob("*.md")):
            title = path.stem
            for block in path.read_text(encoding="utf-8").split("\n\n"):
                block = block.strip()
                if block.startswith("#"):
                    title = block.splitlines()[0].lstrip("# ").strip()
                    block = "\n".join(block.splitlines()[1:]).strip()
                if block:
                    self.chunks.append(Chunk(f"kb/{path.name}#{title}", title, block))
        self.docs = [tokens(c.title + " " + c.text) for c in self.chunks]
        self.avg = sum(map(len, self.docs)) / max(len(self.docs), 1)
        df = {}
        for d in self.docs:
            for t in set(d):
                df[t] = df.get(t, 0) + 1
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def search(self, query, k=2, min_score=1.0):
        q = tokens(query)
        scored = []
        for chunk, d in zip(self.chunks, self.docs):
            s = 0.0
            for t in q:
                tf = d.count(t)
                if tf:
                    s += self.idf[t] * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * len(d) / self.avg))
            if s >= min_score:
                scored.append((s, chunk))
        scored.sort(key=lambda x: -x[0])
        return [c for _, c in scored[:k]]
