from aiogram import Router
from .registration import router as registration_router
from .payment import router as payment_router
from .subscription import router as subscription_router
from .admin import router as admin_router
from .chat_events import router as chat_events_router

routers = [
    registration_router,
    payment_router,
    subscription_router,
    admin_router,
    chat_events_router,
]
