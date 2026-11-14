from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
from app.db import Session
from app.models import User, Deal
from app.config import settings
from app.keyboards import main_menu, back_menu

router = Router()

async def ensure_user(telegram_id: int, username: str | None):
    async with Session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(telegram_id=telegram_id, username=username)
            session.add(user)
            await session.commit()
        return user.id

@router.message(CommandStart())
async def start(message: Message):
    async with Session() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(telegram_id=message.from_user.id, username=message.from_user.username)
            session.add(user)
            await session.flush()

        payload = (message.text or "").partition(" ")[2].strip()
        if payload.startswith("deal_"):
            code = payload[5:]
            result = await session.execute(select(Deal).where(Deal.public_code == code))
            deal = result.scalar_one_or_none()
            if deal is None:
                await message.answer("Сделка не найдена.", reply_markup=main_menu())
                await session.commit()
                return
            if deal.seller_id == user.id:
                await message.answer(f"Это ваша сделка #{code}.", reply_markup=main_menu())
            elif deal.buyer_id is not None and deal.buyer_id != user.id:
                await message.answer("К этой сделке уже присоединился другой покупатель.", reply_markup=main_menu())
            elif deal.status.value != "waiting_for_buyer":
                await message.answer(f"Сделка сейчас недоступна: {deal.status.value}.", reply_markup=main_menu())
            else:
                deal.buyer_id = user.id
                deal.status = type(deal.status).AWAITING_PAYMENT
                await message.answer(
                    f"Вы присоединились к сделке #{code}.\n"
                    f"Сумма: {deal.amount_nano / 1e9:g} TON\n"
                    f"Описание: {deal.description}\n\n"
                    "Это тестовый режим: приём средств ещё не включён.",
                    reply_markup=main_menu()
                )
        else:
            await session.commit()
            await message.answer(
                f"✨ Добро пожаловать в {settings.bot_display_name}!\n"
                "Безопасное сопровождение OTC-сделок.\n\n"
                f"Сеть: TON {settings.ton_network}  •  Комиссия: {settings.escrow_fee_bps / 100:.2f}%\n"
                f"Менеджер всех сделок: @{settings.manager_username}\n"
                "Тестовый режим — реальные средства не принимаются.",
                reply_markup=main_menu()
            )
            return
        await session.commit()

@router.callback_query(F.data == "menu:home")
async def menu_home(callback: CallbackQuery):
    await callback.message.edit_text(
        f"✨ {settings.bot_display_name}\nГлавное меню\n\n"
        f"Сеть: TON {settings.ton_network} • Комиссия: {settings.escrow_fee_bps / 100:.2f}%\n"
        "Тестовый режим — реальные средства не принимаются.",
        reply_markup=main_menu()
    )
    await callback.answer()

@router.callback_query(F.data == "menu:create")
async def menu_create(callback: CallbackQuery):
    await callback.message.edit_text(
        "➕ Создание сделки\n\n"
        "Отправьте команду в формате:\n"
        "/createdemo сумма описание\n\n"
        "Например: /createdemo 2.5 Telegram gift\n\n"
        "Сейчас создаются только тестовые сделки без приёма TON.",
        reply_markup=back_menu()
    )
    await callback.answer()

@router.callback_query(F.data == "menu:deals")
async def menu_deals(callback: CallbackQuery):
    await callback.message.answer("Ваши сделки: используйте /mydeals")
    await callback.answer()

@router.callback_query(F.data == "menu:profile")
async def menu_profile(callback: CallbackQuery):
    async with Session() as session:
        result = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
        user = result.scalar_one_or_none()
        if user:
            result = await session.execute(
                select(Deal).where((Deal.seller_id == user.id) | (Deal.buyer_id == user.id))
            )
            count = len(result.scalars().all())
        else:
            count = 0
    username = f"@{callback.from_user.username}" if callback.from_user.username else "не указан"
    await callback.message.edit_text(
        "👤 Ваш профиль\n\n"
        f"Telegram ID: {callback.from_user.id}\n"
        f"Имя пользователя: {username}\n"
        f"Количество сделок: {count}\n"
        f"Баланс: {user.balance_ton_nano / 1e9:.4f} TON • {user.balance_rub_kopecks / 100:.2f} RUB • {user.balance_stars} Stars\n"
        "Баланс — внутренний учёт; реальные пополнения/выводы пока не подключены.",
        reply_markup=back_menu()
    )
    await callback.answer()

@router.callback_query(F.data == "menu:help")
async def menu_help(callback: CallbackQuery):
    await callback.message.edit_text(
        "ℹ️ Помощь Prime Bot\n\n"
        "/newdeal — инструкция по созданию сделки\n"
        "/createdemo сумма описание — создать тестовую сделку\n"
        "/mydeals — список ваших сделок\n"
        "/deal КОД — подробности сделки\n"
        "/dispute КОД — открыть спор\n\n"
        "Поддержка: обратитесь к администратору проекта.",
        reply_markup=back_menu()
    )
    await callback.answer()
