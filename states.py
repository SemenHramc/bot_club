from aiogram.fsm.state import State, StatesGroup

class RegistrationState(StatesGroup):
    fio = State()
    phone = State()
    email = State()
    consent = State()

class PaymentState(StatesGroup):
    select_period = State()
    promo_code = State()
    confirm = State()
