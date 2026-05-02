import re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from states import RegistrationState
from keyboards import (
    get_consent_keyboard,
    get_main_menu_keyboard,
    get_phone_keyboard,
    get_cancel_keyboard,
)
from database import SessionLocal
from models import User
from config import ADMIN_IDS

router = Router()

EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@router.message(Command("cancel"))
@router.message(F.text == "❌ Отмена")
async def cancel_registration(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.clear()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        is_admin = message.from_user.id in ADMIN_IDS
        if user:
            await message.answer(
                "❌ Действие отменено.",
                reply_markup=get_main_menu_keyboard(is_admin=is_admin),
            )
        else:
            await message.answer(
                "❌ Действие отменено. Чтобы начать регистрацию, нажмите /start",
                reply_markup=ReplyKeyboardRemove(),
            )
    finally:
        db.close()


@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        if user:
            is_admin = message.from_user.id in ADMIN_IDS
            await message.answer(
                f"👋 С возвращением, {user.fio}!\n\n" "Выберите действие:",
                reply_markup=get_main_menu_keyboard(is_admin=is_admin),
            )
        else:
            await message.answer(
                "👋 Добро пожаловать в закрытый клуб!\n\n"
                "Для доступа необходимо пройти регистрацию.\n"
                "Пожалуйста, введите ваше ФИО:\n\n"
                "<i>Отправьте /cancel для отмены</i>",
                reply_markup=get_cancel_keyboard(),
                parse_mode="HTML",
            )
            await state.set_state(RegistrationState.fio)
    finally:
        db.close()


@router.message(RegistrationState.fio)
async def process_fio(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        return

    fio = message.text.strip()
    if len(fio) < 2 or len(fio) > 100:
        await message.answer(
            "❌ ФИО должно быть от 2 до 100 символов. Попробуйте снова:",
            reply_markup=get_cancel_keyboard(),
        )
        return

    await state.update_data(fio=fio)
    await message.answer(
        "📱 Пожалуйста, поделитесь вашим номером телефона:",
        reply_markup=get_phone_keyboard(),
    )
    await state.set_state(RegistrationState.phone)


@router.message(RegistrationState.phone, F.contact)
async def process_phone(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    await state.update_data(phone=phone)
    await message.answer(
        "📧 Введите ваш email:\n\n" "<i>Отправьте /cancel для отмены</i>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(RegistrationState.email)


@router.message(RegistrationState.phone)
async def process_phone_text(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        return
    await message.answer(
        "Пожалуйста, используйте кнопку '📱 Отправить номер' для отправки контакта."
    )


@router.message(RegistrationState.email)
async def process_email(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        return

    email = message.text.strip().lower()
    if not EMAIL_REGEX.match(email):
        await message.answer(
            "❌ Пожалуйста, введите корректный email:",
            reply_markup=get_cancel_keyboard(),
        )
        return

    await state.update_data(email=email)
    await message.answer(
        "📋 Для продолжения необходимо дать согласие на обработку персональных данных.\n\n"
        "Вы согласны?",
        reply_markup=get_consent_keyboard(),
    )
    await state.set_state(RegistrationState.consent)


@router.callback_query(RegistrationState.consent, F.data == "consent_yes")
async def process_consent_yes(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    db = SessionLocal()
    try:
        user = User(
            telegram_id=callback.from_user.id,
            fio=data["fio"],
            phone=data["phone"],
            email=data["email"],
            consent_given=True,
        )
        db.add(user)
        db.commit()

        is_admin = callback.from_user.id in ADMIN_IDS
        await callback.message.edit_text(
            "✅ Регистрация завершена!\n\n"
            f"• ФИО: <b>{user.fio}</b>\n"
            f"• Телефон: <code>{user.phone}</code>\n"
            f"• Email: <code>{user.email}</code>\n\n"
            "Выберите действие:",
            reply_markup=get_main_menu_keyboard(is_admin=is_admin),
            parse_mode="HTML",
        )
    finally:
        db.close()

    await state.clear()
    await callback.answer()


@router.callback_query(RegistrationState.consent, F.data == "consent_no")
async def process_consent_no(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "❌ Без согласия на обработку данных мы не можем продолжить.\n\n"
        "Если передумаете — нажмите /start"
    )
    await state.clear()
    await callback.answer()
