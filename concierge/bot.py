"""Telegram-бот на aiogram 3. Запуск: python -m concierge.bot (нужен .env)."""
import asyncio, os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from .agent import Concierge, make_llm

def fmt(r):
    return r["text"] + "\n\nИсточник: " + ", ".join(r["sources"])

async def main():
    bot = Bot(os.environ["BOT_TOKEN"])
    operators = int(os.environ["OPERATOR_CHAT_ID"])
    c = Concierge(os.getenv("KB_DIR", "kb"), os.getenv("JOURNAL", "data/journal.jsonl"), make_llm())
    dp = Dispatcher()

    async def notify(r, m):
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"ok:{r['ticket']}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"no:{r['ticket']}")]])
        await bot.send_message(operators, f"Заявка #{r['ticket']} ({r['reason']})\n«{m.text}»\nПредлагаю: {r['proposed_action']}", reply_markup=kb)

    @dp.message(F.text)
    async def on_text(m: Message):
        r = c.answer(m.from_user.id, m.text)
        if r["type"] == "answer":
            await m.answer(fmt(r))
            if "ticket" in r:
                await notify(r["ticket"], m)
                await m.answer("Передал сотруднику, он подтвердит действие.")
        else:
            await notify(r, m)
            await m.answer("Не нашёл ответа в базе — передал сотруднику.")

    @dp.callback_query(F.data.regexp(r"^(ok|no):\d+$"))
    async def on_decide(q: CallbackQuery):
        kind, tid = q.data.split(":")
        t = c.decide(int(tid), q.from_user.id, kind == "ok")
        if t is None:
            return await q.answer("Уже обработано")
        await bot.send_message(t["user"], "Сотрудник подтвердил действие." if kind == "ok" else "Сотрудник ответит вам лично.")
        await q.message.edit_text(q.message.text + ("\n✅ подтверждено" if kind == "ok" else "\n❌ отклонено"))
        await q.answer()

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
