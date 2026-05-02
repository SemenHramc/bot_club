from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from keyboards import get_main_menu_keyboard, get_subscription_keyboard
from payment_service import PaymentService
from database import SessionLocal
from models import Subscription, User
from datetime import datetime, timezone
from config import ADMIN_IDS

router = Router()


@router.callback_query(F.data == "my_subscription")
async def my_subscription(callback: CallbackQuery):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            await callback.message.edit_text(
                "❌ Пользователь не найден. Нажмите /start для регистрации.",
                reply_markup=get_main_menu_keyboard(),
            )
            await callback.answer()
            return

        sub = PaymentService.get_active_subscription(user.id)

        if sub:
            days_left = (sub.end_date - datetime.now(timezone.utc)).days + 1
            status_emoji = "✅" if sub.status == "active" else "❌"
            await callback.message.edit_text(
                f"📅 <b>Ваша подписка</b>\n\n"
                f"{status_emoji} Статус: <b>{'Активна' if sub.status == 'active' else 'Неактивна'}</b>\n"
                f"📆 Действует до: <b>{sub.end_date.strftime('%d.%m.%Y %H:%M')}</b>\n"
                f"⏳ Осталось дней: <b>{days_left}</b>\n\n"
                "Если хотите продлить — нажмите кнопку ниже.",
                reply_markup=get_subscription_keyboard(
                    has_active=True, is_admin=callback.from_user.id in ADMIN_IDS
                ),
                parse_mode="HTML",
            )
        else:
            await callback.message.edit_text(
                "❌ У вас нет активной подписки.\n\n"
                "Нажмите <b>Купить подписку</b> для получения доступа.",
                reply_markup=get_subscription_keyboard(
                    has_active=False, is_admin=callback.from_user.id in ADMIN_IDS
                ),
                parse_mode="HTML",
            )
    finally:
        db.close()

    await callback.answer()


@router.callback_query(F.data == "main_menu")
async def main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    is_admin = callback.from_user.id in ADMIN_IDS
    await callback.message.edit_text(
        "👋 <b>Главное меню</b>\n\n" "Выберите действие:",
        reply_markup=get_main_menu_keyboard(is_admin=is_admin),
        parse_mode="HTML",
    )
    await callback.answer()
