"""Database provisioning and Stripe webhook event handling."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.billing import (
    BillingCheckoutSession,
    BillingCustomer,
    BillingEvent,
    BillingSubscription,
    PendingUserInvite,
)
from app.models.organization import Organization
from app.services.billing.slug import unique_org_slug

logger = logging.getLogger(__name__)


def _utc_from_unix(ts: int | None) -> datetime | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


class BillingService:
    def __init__(self, db: Session):
        self.db = db

    def record_checkout_session(
        self,
        *,
        stripe_checkout_session_id: str,
        customer_email: str,
        plan: str,
        billing_interval: str,
        organization_id: uuid.UUID | None = None,
    ) -> BillingCheckoutSession:
        row = BillingCheckoutSession(
            stripe_checkout_session_id=stripe_checkout_session_id,
            organization_id=organization_id,
            customer_email=customer_email.lower(),
            plan=plan,
            billing_interval=billing_interval,
            status="open",
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def get_account_summary(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        stripe_customer_id: str | None = None,
        email: str | None = None,
    ) -> dict[str, Any] | None:
        org: Organization | None = None
        if organization_id:
            org = self.db.get(Organization, organization_id)
        elif stripe_customer_id:
            org = self.db.scalar(
                select(Organization).where(Organization.stripe_customer_id == stripe_customer_id).limit(1)
            )
        elif email:
            customer = self.db.scalar(
                select(BillingCustomer)
                .where(BillingCustomer.email == email.lower())
                .order_by(BillingCustomer.created_at.desc())
                .limit(1)
            )
            if customer and customer.organization_id:
                org = self.db.get(Organization, customer.organization_id)

        if org is None:
            return None

        sub = self.db.scalar(
            select(BillingSubscription)
            .where(BillingSubscription.organization_id == org.id)
            .order_by(BillingSubscription.created_at.desc())
            .limit(1)
        )

        return {
            "organization_id": str(org.id),
            "organization_name": org.name,
            "slug": org.slug,
            "status": org.status,
            "plan": org.plan,
            "stripe_customer_id": org.stripe_customer_id,
            "stripe_subscription_id": org.stripe_subscription_id,
            "subscription": None
            if sub is None
            else {
                "status": sub.status,
                "billing_interval": sub.billing_interval,
                "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
                "cancel_at_period_end": sub.cancel_at_period_end,
            },
        }

    def begin_event(self, stripe_event_id: str, event_type: str, payload: dict[str, Any]) -> BillingEvent | None:
        existing = self.db.scalar(
            select(BillingEvent).where(BillingEvent.stripe_event_id == stripe_event_id).limit(1)
        )
        if existing:
            return None

        obj = payload.get("data", {}).get("object", {})
        row = BillingEvent(
            stripe_event_id=stripe_event_id,
            event_type=event_type,
            stripe_customer_id=obj.get("customer") if isinstance(obj.get("customer"), str) else None,
            stripe_subscription_id=obj.get("subscription") or obj.get("id")
            if event_type.startswith("customer.subscription")
            else obj.get("subscription"),
            payload_json=payload,
            status="processing",
        )
        if isinstance(row.stripe_subscription_id, dict):
            row.stripe_subscription_id = None
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def complete_event(self, event_row: BillingEvent, *, organization_id: uuid.UUID | None = None) -> None:
        event_row.status = "processed"
        event_row.processed_at = datetime.now(timezone.utc)
        if organization_id:
            event_row.organization_id = organization_id
        self.db.commit()

    def fail_event(self, event_row: BillingEvent, message: str) -> None:
        event_row.status = "failed"
        event_row.error_message = message[:2000]
        event_row.processed_at = datetime.now(timezone.utc)
        self.db.commit()

    def process_stripe_event(self, event_type: str, payload: dict[str, Any], event_row: BillingEvent) -> uuid.UUID | None:
        handlers = {
            "checkout.session.completed": self._handle_checkout_completed,
            "customer.subscription.created": self._handle_subscription_upsert,
            "customer.subscription.updated": self._handle_subscription_upsert,
            "customer.subscription.deleted": self._handle_subscription_deleted,
            "invoice.payment_succeeded": self._handle_invoice_payment_succeeded,
            "invoice.payment_failed": self._handle_invoice_payment_failed,
            "customer.updated": self._handle_customer_updated,
        }
        handler = handlers.get(event_type)
        if handler is None:
            self.complete_event(event_row)
            return event_row.organization_id

        org_id = handler(payload, event_row)
        self.complete_event(event_row, organization_id=org_id)
        return org_id

    def provision_from_checkout(
        self,
        *,
        stripe_customer_id: str,
        stripe_subscription_id: str | None,
        customer_email: str,
        company_name: str,
        plan: str,
        billing_interval: str,
        hubspot_contact_id: str | None = None,
        hubspot_company_id: str | None = None,
        hubspot_deal_id: str | None = None,
        customer_name: str | None = None,
        stripe_price_id: str | None = None,
        stripe_product_id: str | None = None,
        subscription_status: str = "active",
        current_period_start: datetime | None = None,
        current_period_end: datetime | None = None,
    ) -> Organization:
        billing_customer = self.db.scalar(
            select(BillingCustomer).where(BillingCustomer.stripe_customer_id == stripe_customer_id).limit(1)
        )
        org: Organization | None = None
        if billing_customer and billing_customer.organization_id:
            org = self.db.get(Organization, billing_customer.organization_id)

        if org is None:
            org = self.db.scalar(
                select(Organization).where(Organization.stripe_customer_id == stripe_customer_id).limit(1)
            )

        if org is None:
            org = Organization(
                name=company_name,
                slug=unique_org_slug(self.db, company_name),
                status="active",
                plan=plan,
                stripe_customer_id=stripe_customer_id,
                stripe_subscription_id=stripe_subscription_id,
            )
            self.db.add(org)
            self.db.flush()
        else:
            org.name = company_name or org.name
            org.status = "active"
            org.plan = plan
            org.stripe_customer_id = stripe_customer_id
            if stripe_subscription_id:
                org.stripe_subscription_id = stripe_subscription_id

        if billing_customer is None:
            billing_customer = BillingCustomer(
                organization_id=org.id,
                stripe_customer_id=stripe_customer_id,
                email=customer_email.lower(),
                name=customer_name,
                company_name=company_name,
                hubspot_contact_id=hubspot_contact_id,
                hubspot_company_id=hubspot_company_id,
                hubspot_deal_id=hubspot_deal_id,
            )
            self.db.add(billing_customer)
        else:
            billing_customer.organization_id = org.id
            billing_customer.email = customer_email.lower()
            billing_customer.name = customer_name or billing_customer.name
            billing_customer.company_name = company_name
            billing_customer.hubspot_contact_id = hubspot_contact_id or billing_customer.hubspot_contact_id
            billing_customer.hubspot_company_id = hubspot_company_id or billing_customer.hubspot_company_id
            billing_customer.hubspot_deal_id = hubspot_deal_id or billing_customer.hubspot_deal_id

        if stripe_subscription_id:
            self._upsert_subscription(
                organization=org,
                stripe_customer_id=stripe_customer_id,
                stripe_subscription_id=stripe_subscription_id,
                plan=plan,
                billing_interval=billing_interval,
                status=subscription_status,
                stripe_price_id=stripe_price_id,
                stripe_product_id=stripe_product_id,
                current_period_start=current_period_start,
                current_period_end=current_period_end,
            )

        invite = self.db.scalar(
            select(PendingUserInvite)
            .where(
                PendingUserInvite.organization_id == org.id,
                PendingUserInvite.email == customer_email.lower(),
            )
            .limit(1)
        )
        if invite is None:
            self.db.add(
                PendingUserInvite(
                    organization_id=org.id,
                    email=customer_email.lower(),
                    role="admin",
                    status="pending",
                )
            )

        self.db.commit()
        self.db.refresh(org)
        logger.info(
            "Provisioned organization %s for %s (plan=%s). Send onboarding email manually if auth is not wired.",
            org.id,
            customer_email,
            plan,
        )
        return org

    def _upsert_subscription(
        self,
        *,
        organization: Organization,
        stripe_customer_id: str,
        stripe_subscription_id: str,
        plan: str,
        billing_interval: str,
        status: str,
        stripe_price_id: str | None = None,
        stripe_product_id: str | None = None,
        current_period_start: datetime | None = None,
        current_period_end: datetime | None = None,
        cancel_at_period_end: bool = False,
        canceled_at: datetime | None = None,
        trial_start: datetime | None = None,
        trial_end: datetime | None = None,
    ) -> BillingSubscription:
        sub = self.db.scalar(
            select(BillingSubscription)
            .where(BillingSubscription.stripe_subscription_id == stripe_subscription_id)
            .limit(1)
        )
        if sub is None:
            sub = BillingSubscription(
                organization_id=organization.id,
                stripe_customer_id=stripe_customer_id,
                stripe_subscription_id=stripe_subscription_id,
                plan=plan,
                billing_interval=billing_interval,
                status=status,
            )
            self.db.add(sub)

        sub.stripe_price_id = stripe_price_id or sub.stripe_price_id
        sub.stripe_product_id = stripe_product_id or sub.stripe_product_id
        sub.plan = plan or sub.plan
        sub.billing_interval = billing_interval or sub.billing_interval
        sub.status = status
        sub.current_period_start = current_period_start or sub.current_period_start
        sub.current_period_end = current_period_end or sub.current_period_end
        sub.cancel_at_period_end = cancel_at_period_end
        sub.canceled_at = canceled_at
        sub.trial_start = trial_start or sub.trial_start
        sub.trial_end = trial_end or sub.trial_end

        organization.stripe_subscription_id = stripe_subscription_id
        organization.plan = plan
        self.db.flush()
        return sub

    def _handle_checkout_completed(self, payload: dict[str, Any], event_row: BillingEvent) -> uuid.UUID | None:
        session = payload.get("data", {}).get("object", {})
        metadata = session.get("metadata") or {}
        stripe_customer_id = session.get("customer")
        stripe_subscription_id = session.get("subscription")
        if not stripe_customer_id:
            raise ValueError("checkout.session.completed missing customer id")

        plan = metadata.get("plan", "starter")
        billing_interval = metadata.get("billing_interval", "monthly")
        company_name = metadata.get("company_name") or "SMPL Customer"
        customer_email = (
            metadata.get("customer_email") or session.get("customer_details", {}).get("email") or ""
        ).lower()
        if not customer_email:
            raise ValueError("checkout.session.completed missing customer email")

        org = self.provision_from_checkout(
            stripe_customer_id=str(stripe_customer_id),
            stripe_subscription_id=str(stripe_subscription_id) if stripe_subscription_id else None,
            customer_email=customer_email,
            company_name=company_name,
            plan=plan,
            billing_interval=billing_interval,
            hubspot_contact_id=metadata.get("hubspot_contact_id"),
            hubspot_company_id=metadata.get("hubspot_company_id"),
            hubspot_deal_id=metadata.get("hubspot_deal_id"),
            subscription_status="active",
        )

        checkout_row = self.db.scalar(
            select(BillingCheckoutSession)
            .where(BillingCheckoutSession.stripe_checkout_session_id == session.get("id"))
            .limit(1)
        )
        if checkout_row:
            checkout_row.status = "complete"
            checkout_row.organization_id = org.id
            checkout_row.amount_total = session.get("amount_total")
            checkout_row.currency = session.get("currency")
            checkout_row.completed_at = datetime.now(timezone.utc)

        event_row.stripe_customer_id = str(stripe_customer_id)
        event_row.stripe_subscription_id = (
            str(stripe_subscription_id) if stripe_subscription_id else None
        )
        self.db.commit()
        return org.id

    def _handle_subscription_upsert(self, payload: dict[str, Any], event_row: BillingEvent) -> uuid.UUID | None:
        sub_obj = payload.get("data", {}).get("object", {})
        stripe_subscription_id = sub_obj.get("id")
        stripe_customer_id = sub_obj.get("customer")
        if not stripe_subscription_id or not stripe_customer_id:
            raise ValueError("subscription event missing ids")

        metadata = sub_obj.get("metadata") or {}
        plan = metadata.get("plan") or "starter"
        billing_interval = metadata.get("billing_interval") or (
            "annual" if sub_obj.get("items", {}).get("data", [{}])[0].get("plan", {}).get("interval") == "year"
            else "monthly"
        )

        org = self.db.scalar(
            select(Organization).where(Organization.stripe_customer_id == str(stripe_customer_id)).limit(1)
        )
        if org is None:
            billing_customer = self.db.scalar(
                select(BillingCustomer)
                .where(BillingCustomer.stripe_customer_id == str(stripe_customer_id))
                .limit(1)
            )
            if billing_customer and billing_customer.organization_id:
                org = self.db.get(Organization, billing_customer.organization_id)

        if org is None:
            logger.warning("Subscription event for unknown customer %s", stripe_customer_id)
            return None

        items = sub_obj.get("items", {}).get("data", [])
        price = items[0].get("price", {}) if items else {}

        self._upsert_subscription(
            organization=org,
            stripe_customer_id=str(stripe_customer_id),
            stripe_subscription_id=str(stripe_subscription_id),
            plan=plan,
            billing_interval=billing_interval,
            status=sub_obj.get("status", "active"),
            stripe_price_id=price.get("id"),
            stripe_product_id=price.get("product") if isinstance(price.get("product"), str) else None,
            current_period_start=_utc_from_unix(sub_obj.get("current_period_start")),
            current_period_end=_utc_from_unix(sub_obj.get("current_period_end")),
            cancel_at_period_end=bool(sub_obj.get("cancel_at_period_end")),
            canceled_at=_utc_from_unix(sub_obj.get("canceled_at")),
            trial_start=_utc_from_unix(sub_obj.get("trial_start")),
            trial_end=_utc_from_unix(sub_obj.get("trial_end")),
        )

        if sub_obj.get("status") in ("active", "trialing"):
            org.status = "active"
        elif sub_obj.get("status") in ("past_due", "unpaid"):
            org.status = "past_due"
        self.db.commit()
        return org.id

    def _handle_subscription_deleted(self, payload: dict[str, Any], event_row: BillingEvent) -> uuid.UUID | None:
        sub_obj = payload.get("data", {}).get("object", {})
        stripe_subscription_id = sub_obj.get("id")
        sub = self.db.scalar(
            select(BillingSubscription)
            .where(BillingSubscription.stripe_subscription_id == stripe_subscription_id)
            .limit(1)
        )
        if sub is None:
            return None

        sub.status = "canceled"
        sub.canceled_at = datetime.now(timezone.utc)
        org = self.db.get(Organization, sub.organization_id)
        if org:
            org.status = "canceled"
        self.db.commit()
        return sub.organization_id if sub else None

    def _handle_invoice_payment_succeeded(self, payload: dict[str, Any], event_row: BillingEvent) -> uuid.UUID | None:
        invoice = payload.get("data", {}).get("object", {})
        stripe_customer_id = invoice.get("customer")
        if not stripe_customer_id:
            return None
        org = self.db.scalar(
            select(Organization).where(Organization.stripe_customer_id == str(stripe_customer_id)).limit(1)
        )
        if org:
            org.status = "active"
            self.db.commit()
            return org.id
        return None

    def _handle_invoice_payment_failed(self, payload: dict[str, Any], event_row: BillingEvent) -> uuid.UUID | None:
        invoice = payload.get("data", {}).get("object", {})
        stripe_customer_id = invoice.get("customer")
        if not stripe_customer_id:
            return None
        org = self.db.scalar(
            select(Organization).where(Organization.stripe_customer_id == str(stripe_customer_id)).limit(1)
        )
        if org:
            org.status = "past_due"
            self.db.commit()
            return org.id
        return None

    def _handle_customer_updated(self, payload: dict[str, Any], event_row: BillingEvent) -> uuid.UUID | None:
        customer_obj = payload.get("data", {}).get("object", {})
        stripe_customer_id = customer_obj.get("id")
        email = customer_obj.get("email")
        name = customer_obj.get("name")
        billing_customer = self.db.scalar(
            select(BillingCustomer).where(BillingCustomer.stripe_customer_id == stripe_customer_id).limit(1)
        )
        if billing_customer:
            if email:
                billing_customer.email = email.lower()
            if name:
                billing_customer.name = name
            self.db.commit()
            return billing_customer.organization_id
        return None
