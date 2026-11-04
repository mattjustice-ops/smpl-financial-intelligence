"""The company budget is one row. A stale write does not replace a newer one."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import app.services.budget_working_plan_service as svc


def test_timestamps_match_ignores_sub_centisecond_noise() -> None:
    base = datetime(2026, 11, 4, 18, 0, tzinfo=timezone.utc)
    assert svc.timestamps_match(base, base + timedelta(milliseconds=5))
    assert not svc.timestamps_match(base, base + timedelta(seconds=1))
    assert not svc.timestamps_match(base, None)


class _Db:
    def __init__(self, row):
        self.row = row
        self.committed = False

    def scalars(self, _query):
        return self

    def first(self):
        return self.row

    def add(self, row):
        self.row = row

    def commit(self):
        self.committed = True

    def refresh(self, _row):
        return None

    def rollback(self):
        return None


def _patch_access(monkeypatch) -> None:
    monkeypatch.setattr(svc, "require_org_member", lambda db, oid: (None, uuid.uuid4()))
    monkeypatch.setattr(svc, "get_organization_or_404", lambda db, oid: None)


def test_stale_write_returns_the_saved_plan(monkeypatch) -> None:
    _patch_access(monkeypatch)
    stored = datetime(2026, 11, 4, 18, 0, tzinfo=timezone.utc)
    row = SimpleNamespace(
        budget_year=2027,
        plan_rev=19,
        updated_at=stored,
        levers={"plFlat": {"rd": {"cloud": 1}}},
    )
    db = _Db(row)
    with pytest.raises(HTTPException) as exc:
        svc.save_working_plan(
            db,
            uuid.uuid4(),
            budget_year=2027,
            plan_rev=19,
            levers={"plFlat": {"rd": {"cloud": 2}}},
            base_updated_at=stored - timedelta(minutes=5),
            only_if_empty=False,
        )
    assert exc.value.status_code == 409
    assert exc.value.detail["plan"]["levers"]["plFlat"]["rd"]["cloud"] == 1
    assert db.committed is False


def test_matching_stamp_writes_the_new_levers(monkeypatch) -> None:
    _patch_access(monkeypatch)
    stored = datetime(2026, 11, 4, 18, 0, tzinfo=timezone.utc)
    row = SimpleNamespace(budget_year=2027, plan_rev=19, updated_at=stored, levers={"yoy": 20}, updated_by_user_id=None)
    db = _Db(row)
    out = svc.save_working_plan(
        db,
        uuid.uuid4(),
        budget_year=2027,
        plan_rev=19,
        levers={"yoy": 19},
        base_updated_at=stored,
        only_if_empty=False,
    )
    assert out.levers == {"yoy": 19}
    assert db.committed is True


def test_empty_file_rejects_a_second_creator(monkeypatch) -> None:
    _patch_access(monkeypatch)
    stored = datetime(2026, 11, 4, 18, 0, tzinfo=timezone.utc)
    row = SimpleNamespace(budget_year=2027, plan_rev=19, updated_at=stored, levers={"yoy": 20})
    db = _Db(row)
    with pytest.raises(HTTPException) as exc:
        svc.save_working_plan(
            db,
            uuid.uuid4(),
            budget_year=2027,
            plan_rev=19,
            levers={"yoy": 3},
            base_updated_at=stored,
            only_if_empty=True,
        )
    assert exc.value.status_code == 409
    assert exc.value.detail["plan"]["levers"]["yoy"] == 20
