import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta, timezone
from database import SessionLocal
from models import User, Subscription
from config import GROUP_CHAT_ID
from aiogram import Bot
from keyboards import get_buy_subscription_inline

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()

def setup_scheduler(bot: Bot):
    scheduler.add_job(
        check_expiring_subscriptions,
        CronTrigger(hour=10, minute=0),
        kwargs={"bot": bot},
        id="check_expiring",
        replace_existing=True,
    )
    scheduler.add_job(
        check_expired_subscriptions,
        CronTrigger(hour=11, minute=0),
        kwargs={"bot": bot},
        id="check_expired",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started")

def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down")

async def check_expiring_subscriptions(bot: Bot):
    """Send reminders 3 days before expiration (once per subscription)"""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        reminder_date_start = now + timedelta(days=2, hours=12)  # between 2.5 and 3.5 days
        reminder_date_end = now + timedelta(days=3, hours=12)

        # Find subscriptions expiring in ~3 days, not yet reminded
        subs = db.query(Subscription).filter(
            Subscription.status == "active",
            Subscription.end_date <= reminder_date_end,
            Subscription.end_date > reminder_date_start,
            Subscription.reminder_sent == False,
        ).all()

        for sub in subs:
            sub.reminder_sent = True
            db.commit()

            user = db.query(User).filter(User.id == sub.user_id).first()
            if user:
                days_left = (sub.end_date - now).days + 1
                try:
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=(
                            f"⏰ <b>Напоминание!</b>\n\n"
                            f"Ваша подписка истекает через <b>{days_left} дн.</b>\n"
                            f"📆 Дата окончания: <b>{sub.end_date.strftime('%d.%m.%Y')}</b>\n\n"
                            f"Чтобы не потерять доступ — продлите подписку прямо сейчас."
                        ),
                        reply_markup=get_buy_subscription_inline(),
                        parse_mode="HTML",
                    )
                except Exception as e:
                    logger.error(f"Failed to send reminder to {user.telegram_id}: {e}")
    finally:
        db.close()

async def check_expired_subscriptions(bot: Bot):
    """Remove users from group and notify them"""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        # Find expired subscriptions
        subs = db.query(Subscription).filter(
            Subscription.status == "active",
            Subscription.end_date < now,
        ).all()

        for sub in subs:
            sub.status = "expired"
            db.commit()

            user = db.query(User).filter(User.id == sub.user_id).first()
            if user:
                # Try to remove from group (ban for 30 sec, then unban)
                try:
                    until_ts = int(datetime.now(timezone.utc).timestamp()) + 30
                    await bot.ban_chat_member(
                        chat_id=GROUP_CHAT_ID,
                        user_id=user.telegram_id,
                        until_date=until_ts
                    )
                    # Unban immediately to allow re-join with new invite
                    await bot.unban_chat_member(
                        chat_id=GROUP_CHAT_ID,
                        user_id=user.telegram_id
                    )
                except Exception as e:
                    logger.error(f"Failed to remove user {user.telegram_id} from group: {e}")

                # Notify user
                try:
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=(
                            "❌ <b>Ваша подписка истекла</b>\n\n"
                            "Вы были удалены из закрытой группы.\n\n"
                            "Чтобы продолжить доступ — купите подписку заново."
                        ),
                        reply_markup=get_buy_subscription_inline(),
                        parse_mode="HTML",
                    )
                except Exception as e:
                    logger.error(f"Failed to notify user {user.telegram_id}: {e}")
    finally:
        db.close()
