"""Reusable lightweight dimensions for reporting filters."""

from __future__ import annotations

from dataclasses import dataclass


DIM_SCENARIO = ["Actual", "Budget", "Forecast", "Combined"]

DIM_CHANNEL = [
    "Paid Search",
    "Paid Social",
    "Organic Search",
    "Partner",
    "Webinar",
    "Field Event",
    "Referral",
    "Direct",
    "Content Syndication",
    "Outbound",
    "Customer Success",
]


@dataclass(frozen=True)
class DimensionTable:
    name: str
    values: list[str]


def dim_scenario() -> DimensionTable:
    return DimensionTable("dim_scenario", DIM_SCENARIO)


def dim_channel() -> DimensionTable:
    return DimensionTable("dim_channel", DIM_CHANNEL)
