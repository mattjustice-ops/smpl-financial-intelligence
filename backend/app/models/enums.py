"""Enumerations stored as VARCHAR in PostgreSQL (portable Alembic upgrades)."""

from __future__ import annotations

import enum


class SourceSystem(str, enum.Enum):
    """Upstream system a synced row originated from."""

    SALESFORCE = "salesforce"
    HUBSPOT = "hubspot"
    NETSUITE = "netsuite"
    STRIPE = "stripe"
    CSV = "csv"
    MANUAL = "manual"
    OTHER = "other"


class OpportunityStage(str, enum.Enum):
    """Simplified pipeline stage for analytics (map CRM-specific stages in ETL)."""

    PROSPECTING = "prospecting"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    PAUSED = "paused"


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    VOID = "void"
    UNCOLLECTIBLE = "uncollectible"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


class GlAccountType(str, enum.Enum):
    """High-level classification for IS / BS reporting."""

    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    COGS = "cogs"
    OPEX = "opex"
    OTHER_INCOME_EXPENSE = "other_income_expense"


class GlStatementLine(str, enum.Enum):
    """Whether the account rolls into income statement, balance sheet, or both."""

    INCOME_STATEMENT = "income_statement"
    BALANCE_SHEET = "balance_sheet"
    CASH_FLOW = "cash_flow"
    MEMO = "memo"


class MrrMovementKind(str, enum.Enum):
    NEW = "new"
    EXPANSION = "expansion"
    CONTRACTION = "contraction"
    CHURN = "churn"
    REACTIVATION = "reactivation"


class ForecastScenarioKind(str, enum.Enum):
    BOOKINGS = "bookings"
    REVENUE = "revenue"
    CASH = "cash"


class CommissionPlanRuleKind(str, enum.Enum):
    """How a plan component contributes to commission math."""

    FLAT_RATE_ON_BOOKINGS = "flat_rate_on_bookings"
    TIERED_ON_QUOTA_ATTAINMENT = "tiered_on_quota_attainment"
    SPLIT_ACROSS_REPS = "split_across_reps"
    ACCELERATOR = "accelerator"
    DRAW_AGAINST_COMMISSION = "draw_against_commission"
    OTHER = "other"


class ClawbackTrigger(str, enum.Enum):
    """When clawback is evaluated."""

    INVOICE_DEFAULT = "invoice_default"
    CHURN_WITHIN_WINDOW = "churn_within_window"
    DEAL_REVERSAL = "deal_reversal"
    MANUAL = "manual"


class CommissionPayoutStatus(str, enum.Enum):
    CALCULATED = "calculated"
    APPROVED = "approved"
    PAID = "paid"
    VOID = "void"


class AiCommentaryReportKind(str, enum.Enum):
    EXECUTIVE_SUMMARY = "executive_summary"
    MRR_WATERFALL = "mrr_waterfall"
    BOOKINGS = "bookings"
    REVENUE = "revenue"
    CASH = "cash"
    BOARD_PACK = "board_pack"
    OTHER = "other"
