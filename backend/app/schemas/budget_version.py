"""Budget version API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class BudgetVersionOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    version_name: str
    status: str
    budget_year: int | None = None
    as_of_period: str
    created_by_user_id: uuid.UUID | None = None
    levers: dict[str, Any] | None = None
    table_manifest: list[str] | None = None
    promoted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BudgetDraftCreate(BaseModel):
    version_name: str = Field(min_length=1, max_length=255)
    as_of_period: str | None = None
    budget_year: int | None = None
    levers: dict[str, Any] | None = None
    results: dict[str, Any] | None = None
    tables: dict[str, list[dict[str, Any]]] | None = None
    version_id: uuid.UUID | None = None


class BudgetPromoteResponse(BaseModel):
    version: BudgetVersionOut
    message: str = "Promoted to final and loaded into warehouse."
