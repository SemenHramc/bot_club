import logging
from aiogram import Router
from aiogram.types import ChatMemberUpdated
from database import SessionLocal
from models import User, Subscription
from datetime import datetime, timezone

router = Router()
logger = logging.getLogger(__name__)

@router.my_chat_member()
async def on_my_chat_member(update: ChatMemberUpdated):
    """Track when user leaves the group"""
    # Only process group events
    if update.chat.type not in ("group", "supergroup"):
        return

    # User left the group
    old_status = update.old_chat_member.status if update.old_chat_member else None
    new_status = update.new_chat_member.status if update.new_chat_member else None

    if old_status in ("member", "administrator", "creator") and new_status in ("left", "kicked"):
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.telegram_id == update.from_user.id).first()
            if user:
                # Mark active subscription as expired (user left)
                sub = db.query(Subscription).filter(
                    Subscription.user_id == user.id,
                    Subscription.status == "active",
                    Subscription.end_date > datetime.now(timezone.utc)
                ).first()
                if sub:
                    # Note: we don't expire subscription immediately,
                    # but we log this event
                    logger.info(
                        "User %s left the group while having active subscription until %s",
                        user.telegram_id, sub.end_date
                    )
        finally:
            db.close()
