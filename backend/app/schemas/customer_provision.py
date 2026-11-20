"""Ops request body for sales-led customer provisioning."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field


class ProvisionCustomerRequest(BaseModel):
    customer_number: str = Field(..., min_length=2, max_length=63)
    organization_name: str = Field(..., min_length=1, max_length=255)
    emails: list[str] = Field(..., min_length=1)
    profile: dict[str, Any] | None = None
    contract_ref: str | None = None
    contract_signed_on: str | None = None
    plan: str = "professional"
    role: str = "admin"
    organization_id: uuid.UUID | None = None
    fiscal_year_end_month: int | None = Field(default=None, ge=1, le=12)
