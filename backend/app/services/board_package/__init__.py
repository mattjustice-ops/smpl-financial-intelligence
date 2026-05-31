"""Board reporting package generator: inputs -> JSON package -> .pptx / Google Slides.

Import ``render_pptx_bytes`` from ``app.services.board_package.pptx_builder`` directly.
"""

from app.services.board_package.schemas import (
    ArrBridge,
    BoardPackage,
    BoardPackageInputs,
    BookingsForecastSlide,
    CashForecastSlide,
    ChartSpec,
    ChurnExpansionAnalysis,
    CompanyKpiSummary,
    MrrWaterfallSlide,
    QuotaAttainmentRow,
    RevenueForecastSlide,
    SalesEfficiencySlide,
    SlideContent,
    TableSpec,
)

__all__ = [
    "ArrBridge",
    "BoardPackage",
    "BoardPackageInputs",
    "BookingsForecastSlide",
    "CashForecastSlide",
    "ChartSpec",
    "ChurnExpansionAnalysis",
    "CompanyKpiSummary",
    "MrrWaterfallSlide",
    "QuotaAttainmentRow",
    "RevenueForecastSlide",
    "SalesEfficiencySlide",
    "SlideContent",
    "TableSpec",
]
