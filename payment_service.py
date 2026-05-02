import hashlib
import aiohttp
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from config import T_BANK_TERMINAL_KEY, T_BANK_SECRET, BASE_PRICE, PAYMENT_TEST_MODE, SUBSCRIPTION_PERIODS
from database import SessionLocal
from models import Payment, PromoCode, User, Subscription

class PaymentService:
    @staticmethod
    def calculate_price(period_key: int, promo_code: str = None):
        base = BASE_PRICE * SUBSCRIPTION_PERIODS[period_key]["multiplier"]
        discount = Decimal("0")

        if promo_code:
            db = SessionLocal()
            try:
                promo = db.query(PromoCode).filter(
                    PromoCode.code == promo_code.upper(),
                    PromoCode.active == True
                ).first()
                if promo:
                    discount = Decimal(str(promo.discount_value))
            finally:
                db.close()

        final = max(Decimal("0"), Decimal(str(base)) - discount)
        return {
            "base": base,
            "discount": float(discount),
            "final": float(final),
            "promo_valid": discount > 0,
        }

    @staticmethod
    async def create_payment(user_id: int, amount: float, period_key: int, promo_code: str = None):
        db = SessionLocal()
        try:
            price_info = PaymentService.calculate_price(period_key, promo_code)

            payment = Payment(
                user_id=user_id,
                amount=amount,
                promo_code=promo_code.upper() if promo_code else None,
                discount=price_info["discount"],
                period_months=SUBSCRIPTION_PERIODS[period_key]["months"],
                status="pending"
            )
            db.add(payment)
            db.commit()
            db.refresh(payment)

            if PAYMENT_TEST_MODE or not T_BANK_TERMINAL_KEY:
                # Test mode: simulate payment link
                payment.payment_id = f"TEST_{payment.id}_{int(datetime.now(timezone.utc).timestamp())}"
                db.commit()
                return {
                    "success": True,
                    "payment_id": payment.id,
                    "test_url": f"/test_pay/{payment.id}",
                    "message": "💳 Тестовый режим оплаты. Нажмите кнопку ниже для подтверждения оплаты."
                }

            # Real T-Bank integration
            return await PaymentService._create_tbank_payment(payment, amount)
        finally:
            db.close()

    @staticmethod
    async def _create_tbank_payment(payment: Payment, amount: float):
        data = {
            "TerminalKey": T_BANK_TERMINAL_KEY,
            "Amount": int(amount * 100),  # kopecks
            "OrderId": str(payment.id),
            "Description": f"Подписка в закрытый клуб #{payment.id}",
        }

        # Generate token (T-Bank token format)
        token_str = f"{T_BANK_SECRET}{payment.id}{int(amount * 100)}{T_BANK_TERMINAL_KEY}"
        data["Token"] = hashlib.sha256(token_str.encode()).hexdigest()

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://securepay.tinkoff.ru/v2/Init",
                json=data
            ) as resp:
                result = await resp.json()
                if result.get("Success"):
                    db = SessionLocal()
                    try:
                        # Refresh detached object in new session
                        db_payment = db.query(Payment).filter(Payment.id == payment.id).first()
                        if db_payment:
                            db_payment.payment_id = result.get("PaymentId")
                            db.commit()
                    finally:
                        db.close()
                    return {
                        "success": True,
                        "payment_id": payment.id,
                        "url": result.get("PaymentURL"),
                        "message": "Перейдите по ссылке для оплаты"
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Ошибка создания платежа: {result.get('Message', 'Unknown')}"
                    }

    @staticmethod
    async def process_test_payment(payment_id: int):
        db = SessionLocal()
        try:
            payment = db.query(Payment).filter(Payment.id == payment_id).first()
            if not payment or payment.status != "pending":
                return False

            payment.status = "success"
            db.commit()

            # Create or extend subscription
            await PaymentService._activate_subscription(db, payment)
            return True
        finally:
            db.close()

    @staticmethod
    async def _activate_subscription(db, payment: Payment):
        user = db.query(User).filter(User.id == payment.user_id).first()

        months = payment.period_months or 1

        # Check existing subscription
        existing = db.query(Subscription).filter(
            Subscription.user_id == user.id,
            Subscription.status == "active"
        ).order_by(Subscription.end_date.desc()).first()

        now = datetime.now(timezone.utc)
        if existing and existing.end_date > now:
            start_date = existing.end_date
        else:
            start_date = now

        end_date = start_date + timedelta(days=30 * months)
        # Set to end of day
        end_date = end_date.replace(hour=23, minute=59, second=59)

        sub = Subscription(
            user_id=user.id,
            start_date=start_date,
            end_date=end_date,
            status="active"
        )
        db.add(sub)
        db.commit()

        # Increment promo usage
        if payment.promo_code:
            promo = db.query(PromoCode).filter(PromoCode.code == payment.promo_code).first()
            if promo:
                promo.usage_count += 1
                db.commit()

        return sub

    @staticmethod
    def get_active_subscription(user_id: int):
        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            sub = db.query(Subscription).filter(
                Subscription.user_id == user_id,
                Subscription.status == "active",
                Subscription.end_date > now
            ).order_by(Subscription.end_date.desc()).first()
            return sub
        finally:
            db.close()
