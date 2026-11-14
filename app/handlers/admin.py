from decimal import Decimal, InvalidOperation
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select, func
from app.config import settings
from app.db import Session
from app.models import User, Deal, DealStatus, BalanceTransaction

router = Router()

CURRENCY_META = {
    "TON": ("balance_ton_nano", Decimal("1000000000"), 4),
    "RUB": ("balance_rub_kopecks", Decimal("100"), 2),
    "STARS": ("balance_stars", Decimal("1"), 0),
}

def is_admin(telegram_id: int) -> bool:
    return telegram_id in settings.admin_id_set

def parse_amount(value: str, currency: str) -> int:
    amount = Decimal(value.replace(",", "."))
    if amount <= 0:
        raise ValueError
    field, multiplier, _ = CURRENCY_META[currency]
    minor = amount * multiplier
    if minor != minor.to_integral_value():
        raise ValueError
    return int(minor)

def format_balance(user: User) -> str:
    return (f"TON: {user.balance_ton_nano / 1e9:.4f}\n"
            f"RUB: {user.balance_rub_kopecks / 100:.2f}\n"
            f"Stars: {user.balance_stars}")

@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ только администратору.")
        return
    async with Session() as session:
        users = await session.scalar(select(func.count(User.id))) or 0
        deals = await session.scalar(select(func.count(Deal.id))) or 0
        disputed = await session.scalar(select(func.count(Deal.id)).where(Deal.status == DealStatus.DISPUTED)) or 0
    await message.answer(
        "🛠 PRIME BOT — АДМИН-ПАНЕЛЬ\n\n"
        f"Пользователей: {users}\nСделок: {deals}\nСпоров: {disputed}\n\n"
        "Команды:\n"
        "/user ID — баланс пользователя\n"
        "/credit ID TON|RUB|STARS сумма причина — пополнить внутренний баланс\n"
        "/debit ID TON|RUB|STARS сумма причина — списать внутренний баланс\n"
        "/transactions ID — история баланса\n"
        "/nftreceived КОД — NFT получен менеджером\n"
        "/nftverified КОД — NFT проверен вручную\n"
        "/nftdelivered КОД — передача покупателю подтверждена\n\n"
        f"Главный менеджер: @{settings.manager_username}\n"
        "Внимание: операции с балансом — внутренний учёт, не фактическое движение денег."
    )

@router.message(Command("user"))
async def user_balance(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа."); return
    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Формат: /user TELEGRAM_ID"); return
    async with Session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == int(parts[1])))
        if not user:
            await message.answer("Пользователь не найден."); return
        await message.answer(f"Пользователь: {user.telegram_id} (@{user.username or 'нет'})\n{format_balance(user)}")

async def change_balance(message: Message, action: str):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа."); return
    parts = (message.text or "").split(maxsplit=4)
    if len(parts) < 4 or not parts[1].isdigit():
        await message.answer(f"Формат: /{action} TELEGRAM_ID TON|RUB|STARS сумма причина"); return
    telegram_id = int(parts[1]); currency = parts[2].upper()
    if currency not in CURRENCY_META:
        await message.answer("Валюта: TON, RUB или STARS."); return
    try:
        minor = parse_amount(parts[3], currency)
    except (InvalidOperation, ValueError):
        await message.answer("Некорректная сумма или слишком много знаков после запятой."); return
    reason = parts[4] if len(parts) > 4 else "Ручная операция администратора"
    field, _, _ = CURRENCY_META[currency]
    async with Session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id).with_for_update())
        if not user:
            await message.answer("Пользователь не найден. Он должен сначала запустить бота через /start."); return
        delta = minor if action == "credit" else -minor
        if getattr(user, field) + delta < 0:
            await message.answer("Недостаточно средств для списания."); return
        setattr(user, field, getattr(user, field) + delta)
        session.add(BalanceTransaction(user_id=user.id, currency=currency, amount_minor=minor,
                    action=action, reason=reason[:256], admin_telegram_id=message.from_user.id))
        await session.commit()
        balance = format_balance(user)
    await message.answer(f"✅ Операция записана.\nПользователь: {telegram_id}\n{currency}: {'+' if action == 'credit' else '-'}{parts[3]}\n\nНовый баланс:\n{balance}")

@router.message(Command("credit"))
async def credit(message: Message):
    await change_balance(message, "credit")

@router.message(Command("debit"))
async def debit(message: Message):
    await change_balance(message, "debit")

@router.message(Command("transactions"))
async def transactions(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа."); return
    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Формат: /transactions TELEGRAM_ID"); return
    async with Session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == int(parts[1])))
        if not user:
            await message.answer("Пользователь не найден."); return
        rows = (await session.scalars(select(BalanceTransaction).where(BalanceTransaction.user_id == user.id)
                                      .order_by(BalanceTransaction.id.desc()).limit(20))).all()
    if not rows:
        await message.answer("История операций пуста."); return
    lines = [f"{r.action} {r.currency} {r.amount_minor} minor — {r.reason}" for r in rows]
    await message.answer("Последние операции (до 20):\n" + "\n".join(lines))

async def set_deal_stage(message: Message, command: str, status: DealStatus, label: str):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Только менеджер/администратор может подтверждать этапы."); return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) != 2:
        await message.answer(f"Формат: /{command} КОД"); return
    async with Session() as session:
        deal = await session.scalar(select(Deal).where(Deal.public_code == parts[1].strip()))
        if not deal:
            await message.answer("Сделка не найдена."); return
        deal.status = status
        await session.commit()
    await message.answer(f"✅ Сделка #{parts[1]}: {label}. Отметка внесена вручную.")

@router.message(Command("nftreceived"))
async def nft_received(message: Message):
    await set_deal_stage(message, "nftreceived", DealStatus.NFT_RECEIVED, "NFT получен менеджером (ручная отметка)")

@router.message(Command("nftverified"))
async def nft_verified(message: Message):
    await set_deal_stage(message, "nftverified", DealStatus.NFT_VERIFIED, "NFT проверен менеджером вручную")

@router.message(Command("nftdelivered"))
async def nft_delivered(message: Message):
    await set_deal_stage(message, "nftdelivered", DealStatus.NFT_DELIVERED, "передача покупателю подтверждена менеджером")
