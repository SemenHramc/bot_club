from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from config import SUBSCRIPTION_PERIODS, BASE_PRICE


def get_main_menu_keyboard(is_admin=False):
    buttons = [
        [InlineKeyboardButton(text="💳 Купить подписку", callback_data="buy_subscription")],
        [InlineKeyboardButton(text="📅 Моя подписка", callback_data="my_subscription")],
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_period_keyboard():
    buttons = []
    for key, period in SUBSCRIPTION_PERIODS.items():
        price = BASE_PRICE * period["multiplier"]
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{period['label']} — {price:,} ₽".replace(",", " "),
                    callback_data=f"period_{key}",
                )
            ]
        )
    buttons.append([InlineKeyboardButton(text="🔙 Назад в меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_promo_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎫 У меня есть промокод", callback_data="has_promo")],
            [InlineKeyboardButton(text="⏩ Пропустить", callback_data="skip_promo")],
            [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="main_menu")],
        ]
    )


def get_payment_keyboard(payment_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💰 Оплатить", callback_data=f"pay_{payment_id}")],
            [InlineKeyboardButton(text="🔙 Отмена", callback_data="main_menu")],
        ]
    )


def get_consent_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Согласен", callback_data="consent_yes")],
            [InlineKeyboardButton(text="❌ Не согласен", callback_data="consent_no")],
        ]
    )


def get_admin_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton(text="🎫 Промокоды", callback_data="admin_promos")],
            [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
            [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="main_menu")],
        ]
    )


def get_phone_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Отправить номер", request_contact=True)],
            [KeyboardButton(text="❌ Отмена")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_subscription_keyboard(has_active: bool = False, is_admin: bool = False):
    buttons = []
    if has_active:
        buttons.append(
            [InlineKeyboardButton(text="💳 Продлить подписку", callback_data="buy_subscription")]
        )
    else:
        buttons.append(
            [InlineKeyboardButton(text="💳 Купить подписку", callback_data="buy_subscription")]
        )
    buttons.append([InlineKeyboardButton(text="🔙 Назад в меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_buy_subscription_inline():
    """Inline-кнопка для сообщений, где нужно предложить купить подписку."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Купить подписку", callback_data="buy_subscription")],
        ]
    )
