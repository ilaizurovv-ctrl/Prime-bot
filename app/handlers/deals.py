import secrets
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select, or_
from app.db import Session
from app.models import Deal, User, DealStatus, NFTKind
from app.config import settings

router = Router()

async def get_user(session, telegram_id: int, username: str | None):
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(telegram_id=telegram_id, username=username)
        session.add(user)
        await session.flush()
    return user

async def save_deal(message: Message, amount_text: str, kind: NFTKind | None,
                    nft_reference: str | None, description: str):
    try:
        amount = float(amount_text)
        if not (0 < amount <= 100000):
            raise ValueError()
        amount_nano = int(amount * 1_000_000_000)
    except ValueError:
        await message.answer("Укажите корректную сумму TON больше нуля.")
        return

    async with Session() as session:
        user = await get_user(session, message.from_user.id, message.from_user.username)
        code = secrets.token_urlsafe(7).replace("-", "").replace("_", "")[:10]
        deal = Deal(
            public_code=code,
            seller_id=user.id,
            amount_nano=amount_nano,
            fee_bps=settings.escrow_fee_bps,
            nft_kind=kind,
            nft_reference=nft_reference,
            description=description,
            status=DealStatus.WAITING_FOR_BUYER,
        )
        session.add(deal)
        await session.commit()

    username = settings.bot_username.lstrip("@")
    invite = f"https://t.me/{username}?start=deal_{code}"
    kind_label = {
        NFTKind.TELEGRAM_GIFT: "Telegram Gift",
        NFTKind.TON_NFT: "TON NFT",
        None: "NFT (тип не указан)",
    }[kind]
    await message.answer(
        f"Тестовая NFT-сделка #{code} создана.\n"
        f"Тип: {kind_label}\n"
        f"NFT reference: {nft_reference or 'не указан'}\n"
        f"Цена: {amount:g} TON\n"
        f"Комиссия: {settings.escrow_fee_bps / 100:.2f}%\n"
        f"Менеджер сделки: @{settings.manager_username}\n"
        f"Передача NFT менеджеру: @{settings.manager_username} (проверка вручную)\n"
        f"Описание: {description}\n\n"
        f"Ссылка покупателю:\n{invite}\n\n"
        "Тестовый режим: владение NFT, приём оплаты и передача NFT пока не проверяются."
    )

@router.message(Command("newdeal"))
async def new_deal_help(message: Message):
    await message.answer(
        "NFT OTC — создание сделки:\n"
        "/createnft gift сумма NFT_ID описание\n"
        "/createnft ton сумма NFT_ADDRESS описание\n\n"
        "Пример:\n/createnft ton 5 EQ... My NFT\n"
        "Сейчас доступны только тестовые записи, без реального Escrow."
    )

@router.message(Command("createnft"))
async def create_nft(message: Message):
    parts = (message.text or "").split(maxsplit=4)
    if len(parts) != 5:
        await message.answer("Формат: /createnft gift|ton сумма NFT_ID_или_ADDRESS описание")
        return
    kind_text, amount_text, nft_reference, description = parts[1:]
    if kind_text.lower() == "gift":
        kind = NFTKind.TELEGRAM_GIFT
    elif kind_text.lower() == "ton":
        kind = NFTKind.TON_NFT
    else:
        await message.answer("Тип NFT должен быть gift или ton.")
        return
    if len(nft_reference) > 256:
        await message.answer("Слишком длинный NFT ID или адрес.")
        return
    await save_deal(message, amount_text, kind, nft_reference, description)

@router.message(Command("createdemo"))
async def create_demo(message: Message):
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) != 3:
        await message.answer("Формат: /createdemo сумма_в_TON описание")
        return
    await save_deal(message, parts[1], None, None, parts[2])

@router.message(Command("mydeals"))
async def my_deals(message: Message):
    async with Session() as session:
        user = await get_user(session, message.from_user.id, message.from_user.username)
        result = await session.execute(
            select(Deal).where(or_(Deal.seller_id == user.id, Deal.buyer_id == user.id))
            .order_by(Deal.id.desc()).limit(15)
        )
        deals = result.scalars().all()
    if not deals:
        await message.answer("У вас пока нет сделок.")
        return
    lines = [
        f"#{d.public_code} — {d.nft_kind.value if d.nft_kind else 'NFT'} — "
        f"{d.amount_nano / 1e9:g} TON — {d.status.value}"
        for d in deals
    ]
    await message.answer("\n".join(lines))

@router.message(Command("deal"))
async def deal_details(message: Message):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) != 2:
        await message.answer("Формат: /deal КОД")
        return
    async with Session() as session:
        result = await session.execute(select(Deal).where(Deal.public_code == parts[1].strip()))
        deal = result.scalar_one_or_none()
        if deal is None:
            await message.answer("Сделка не найдена.")
            return
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        if user is None or user.id not in (deal.seller_id, deal.buyer_id):
            await message.answer("Посмотреть эту сделку могут только её участники.")
            return
        await message.answer(
            f"NFT-сделка #{deal.public_code}\n"
            f"Тип: {deal.nft_kind.value if deal.nft_kind else 'не указан'}\n"
            f"NFT reference: {deal.nft_reference or 'не указан'}\n"
            f"Цена: {deal.amount_nano / 1e9:g} TON\n"
            f"Описание: {deal.description}\n"
            f"Комиссия: {deal.fee_bps / 100:.2f}%\n"
            f"Статус: {deal.status.value}\n"
            f"Менеджер: @{settings.manager_username}\n"
            f"Куда передать NFT: @{settings.manager_username}\n"
            "Тестовая версия: фактическая передача NFT не подтверждается."
        )

@router.message(Command("dispute"))
async def dispute(message: Message):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) != 2:
        await message.answer("Формат: /dispute КОД")
        return
    async with Session() as session:
        result = await session.execute(select(Deal).where(Deal.public_code == parts[1].strip()))
        deal = result.scalar_one_or_none()
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        if deal is None or user is None or user.id not in (deal.seller_id, deal.buyer_id):
            await message.answer("Сделка не найдена или вы не её участник.")
            return
        if deal.status in (DealStatus.COMPLETED, DealStatus.REFUNDED, DealStatus.CANCELLED):
            await message.answer("Завершённую сделку нельзя открыть для спора.")
            return
        deal.status = DealStatus.DISPUTED
        await session.commit()
    await message.answer("Спор зарегистрирован. Администратор должен проверить передачу NFT.")

@router.message(Command("balance"))
async def show_balance(message: Message):
    async with Session() as session:
        user = await get_user(session, message.from_user.id, message.from_user.username)
        await message.answer(
            "💳 Ваш внутренний баланс\n\n"
            f"TON: {user.balance_ton_nano / 1e9:.4f}\n"
            f"RUB: {user.balance_rub_kopecks / 100:.2f}\n"
            f"Stars: {user.balance_stars}\n\n"
            "Это учётные значения. Реальные депозиты и выводы не подключены."
        )
