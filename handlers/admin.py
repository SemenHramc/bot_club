from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from keyboards import get_admin_keyboard, get_main_menu_keyboard
from database import SessionLocal
from models import User, Subscription, Payment, PromoCode
from datetime import datetime, timezone
from config import ADMIN_IDS

router = Router()


@router.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    await callback.message.edit_text(
        "⚙️ <b>Панель администратора</b>\n\n" "Выберите раздел:",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    db = SessionLocal()
    try:
        total_users = db.query(User).count()
        active_subs = (
            db.query(Subscription)
            .filter(
                Subscription.status == "active",
                Subscription.end_date > datetime.now(timezone.utc),
            )
            .count()
        )
        total_payments = db.query(Payment).filter(Payment.status == "success").count()
        total_revenue = (
            db.query(Payment)
            .filter(Payment.status == "success")
            .with_entities(Payment.amount)
            .all()
        )
        total_revenue = sum(float(p[0]) for p in total_revenue) if total_revenue else 0

        await callback.message.edit_text(
            f"📊 <b>Статистика</b>\n\n"
            f"👥 Всего пользователей: <b>{total_users}</b>\n"
            f"✅ Активных подписок: <b>{active_subs}</b>\n"
            f"💰 Успешных платежей: <b>{total_payments}</b>\n"
            f"📈 Выручка: <b>{total_revenue:,.0f} ₽</b>\n\n"
            f"📅 Дата: {datetime.now(timezone.utc).strftime('%d.%m.%Y')}",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML",
        )
    finally:
        db.close()

    await callback.answer()


@router.callback_query(F.data == "admin_promos")
async def admin_promos(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    db = SessionLocal()
    try:
        promos = db.query(PromoCode).all()
        text = "🎫 <b>Промокоды</b>\n\n"
        for p in promos:
            status = "✅ Активен" if p.active else "❌ Неактивен"
            text += (
                f"• Код: <code>{p.code}</code>\n"
                f"  Скидка: <b>{float(p.discount_value):.0f} ₽</b>\n"
                f"  Использований: <b>{p.usage_count}</b>\n"
                f"  Статус: {status}\n"
                f"  Владелец: {p.owner or '—'}\n\n"
            )

        if not promos:
            text += "Промокодов пока нет.\n\n"
            text += "Для создания используйте:\n<code>/add_promo КОД СКИДКА ВЛАДЕЛЕЦ</code>"
        else:
            text += "\nДобавить: <code>/add_promo КОД СКИДКА ВЛАДЕЛЕЦ</code>"

        await callback.message.edit_text(
            text,
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML",
        )
    finally:
        db.close()

    await callback.answer()


@router.message(Command("add_promo"))
async def add_promo(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Нет доступа")
        return

    parts = message.text.split()
    if len(parts) < 3:
        await message.answer(
            "❌ <b>Использование:</b>\n"
            "<code>/add_promo КОД СКИДКА [ВЛАДЕЛЕЦ]</code>\n\n"
            "<b>Пример:</b>\n"
            "<code>/add_promo AMBASSADOR1 500 Иван</code>",
            parse_mode="HTML",
        )
        return

    code = parts[1].upper()
    try:
        discount = float(parts[2])
    except ValueError:
        await message.answer("❌ Скидка должна быть числом")
        return

    owner = parts[3] if len(parts) > 3 else None

    db = SessionLocal()
    try:
        existing = db.query(PromoCode).filter(PromoCode.code == code).first()
        if existing:
            await message.answer(f"❌ Промокод <code>{code}</code> уже существует", parse_mode="HTML")
            return

        promo = PromoCode(
            code=code,
            discount_value=discount,
            owner=owner,
            active=True,
        )
        db.add(promo)
        db.commit()

        await message.answer(
            f"✅ Промокод создан!\n\n"
            f"• Код: <code>{code}</code>\n"
            f"• Скидка: <b>{discount:.0f} ₽</b>\n"
            f"• Владелец: {owner or '—'}",
            parse_mode="HTML",
        )
    finally:
        db.close()


@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    db = SessionLocal()
    try:
        users = db.query(User).order_by(User.created_at.desc()).limit(20).all()
        text = "👥 <b>Последние пользователи</b>\n\n"
        for u in users:
            text += (
                f"• ID: <code>{u.telegram_id}</code>\n"
                f"  ФИО: <b>{u.fio}</b>\n"
                f"  Телефон: <code>{u.phone}</code>\n"
                f"  Email: <code>{u.email}</code>\n"
                f"  Дата: {u.created_at.strftime('%d.%m.%Y')}\n\n"
            )

        if not users:
            text += "Пользователей пока нет."

        await callback.message.edit_text(
            text,
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML",
        )
    finally:
        db.close()

    await callback.answer()
