from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from states import PaymentState
from keyboards import (
    get_period_keyboard,
    get_promo_keyboard,
    get_payment_keyboard,
    get_main_menu_keyboard,
    get_cancel_keyboard,
)
from database import SessionLocal
from models import User, Payment
from payment_service import PaymentService
from config import ADMIN_IDS

router = Router()


@router.callback_query(F.data == "buy_subscription")
async def buy_subscription(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📅 Выберите период подписки:", reply_markup=get_period_keyboard()
    )
    await state.set_state(PaymentState.select_period)
    await callback.answer()


@router.callback_query(PaymentState.select_period, F.data.startswith("period_"))
async def select_period(callback: CallbackQuery, state: FSMContext):
    period_key = int(callback.data.split("_")[1])
    await state.update_data(period_key=period_key)

    price_info = PaymentService.calculate_price(period_key)
    await callback.message.edit_text(
        f"📅 <b>Период:</b> {period_key} мес.\n"
        f"💰 <b>Стоимость:</b> {price_info['final']:.0f} ₽\n\n"
        "У вас есть промокод?",
        reply_markup=get_promo_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(PaymentState.promo_code)
    await callback.answer()


@router.callback_query(PaymentState.promo_code, F.data == "has_promo")
async def ask_promo(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🎫 Введите промокод:\n\n" "<i>Отправьте /cancel для отмены</i>",
        parse_mode="HTML",
    )
    # Отправим reply-кнопку отмены отдельным сообщением (чтобы не мешала редактированию)
    await callback.bot.send_message(
        chat_id=callback.from_user.id,
        text="⬇️ Для отмены нажмите кнопку ниже:",
        reply_markup=get_cancel_keyboard(),
    )
    await callback.answer()


@router.message(PaymentState.promo_code)
async def process_promo(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        return

    promo = message.text.strip().upper()
    data = await state.get_data()
    period_key = data["period_key"]

    price_info = PaymentService.calculate_price(period_key, promo)

    if not price_info["promo_valid"] and promo:
        await message.answer(
            "❌ Промокод не найден или неактивен. Попробуйте другой или нажмите 'Пропустить'.",
            reply_markup=get_cancel_keyboard(),
        )
        return

    await state.update_data(promo_code=promo if price_info["promo_valid"] else None)

    # Create payment
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        result = await PaymentService.create_payment(
            user_id=user.id,
            amount=price_info["final"],
            period_key=period_key,
            promo_code=promo if price_info["promo_valid"] else None,
        )

        payment_id = result["payment_id"]
        await state.update_data(payment_id=payment_id)

        # Убираем reply-клавиатуру отмены
        await message.answer("⏳ Формируем платёж…", reply_markup=ReplyKeyboardRemove())

        if result.get("test_url"):
            keyboard = get_payment_keyboard(payment_id)
            await message.answer(
                f"{result['message']}\n\n"
                f"📅 Период: {period_key} мес.\n"
                f"💰 К оплате: {price_info['final']:.0f} ₽",
                reply_markup=keyboard,
            )
        else:
            await message.answer(
                f"💳 {result['message']}\n" f"Ссылка: {result.get('url', 'N/A')}",
                reply_markup=get_main_menu_keyboard(),
            )
    finally:
        db.close()

    await state.set_state(PaymentState.confirm)


@router.callback_query(PaymentState.promo_code, F.data == "skip_promo")
async def skip_promo(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    period_key = data["period_key"]
    price_info = PaymentService.calculate_price(period_key)

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        result = await PaymentService.create_payment(
            user_id=user.id,
            amount=price_info["final"],
            period_key=period_key,
        )

        payment_id = result["payment_id"]
        await state.update_data(payment_id=payment_id)

        if result.get("test_url"):
            keyboard = get_payment_keyboard(payment_id)
            await callback.message.edit_text(
                f"{result['message']}\n\n"
                f"📅 Период: {period_key} мес.\n"
                f"💰 К оплате: {price_info['final']:.0f} ₽",
                reply_markup=keyboard,
            )
        else:
            await callback.message.edit_text(
                f"💳 {result['message']}\n" f"Ссылка: {result.get('url', 'N/A')}",
                reply_markup=get_main_menu_keyboard(),
            )
    finally:
        db.close()

    await state.set_state(PaymentState.confirm)
    await callback.answer()


@router.callback_query(PaymentState.confirm, F.data.startswith("pay_"))
async def process_payment(callback: CallbackQuery, state: FSMContext):
    payment_id = int(callback.data.split("_")[1])
    success = await PaymentService.process_test_payment(payment_id)

    if success:
        from config import GROUP_CHAT_ID

        # Generate invite link
        try:
            invite = await callback.bot.create_chat_invite_link(
                chat_id=GROUP_CHAT_ID,
                member_limit=1,
            )

            await callback.message.edit_text(
                "✅ Оплата успешно проведена!\n\n"
                "🔗 <b>Ваша ссылка для доступа в группу:</b>\n"
                f"{invite.invite_link}\n\n"
                "⚠️ Ссылка одноразовая. Не передавайте её другим.",
                reply_markup=get_main_menu_keyboard(
                    is_admin=callback.from_user.id in ADMIN_IDS
                ),
                parse_mode="HTML",
            )
        except Exception as e:
            await callback.message.edit_text(
                "✅ Оплата прошла успешно!\n\n"
                "⚠️ Не удалось сгенерировать ссылку автоматически.\n"
                f"Ошибка: {e}\n\n"
                "Обратитесь к администратору.",
                reply_markup=get_main_menu_keyboard(
                    is_admin=callback.from_user.id in ADMIN_IDS
                ),
            )
    else:
        await callback.message.edit_text(
            "❌ Ошибка обработки платежа. Попробуйте позже или обратитесь в поддержку.",
            reply_markup=get_main_menu_keyboard(
                is_admin=callback.from_user.id in ADMIN_IDS
            ),
        )

    await state.clear()
    await callback.answer()
