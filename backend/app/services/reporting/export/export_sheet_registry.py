"""Excel tab lists and report output requirements for board / MD&A exports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CLOSE_PACKAGE_SHEETS = [
    "Executive Summary",
    "KPI Scorecard",
    "Income Statement",
    "Balance Sheet",
    "Cash Flow Statement",
    "Cash Flow Bridge",
    "MRR ARR Waterfall",
    "Pipeline Waterfall",
    "Opportunity Drilldown",
    "Marketing Performance",
    "Revenue Forecast",
    "Bookings Forecast",
    "Deferred Revenue Waterfall",
    "Headcount & Hiring",
    "GL Detail by Department",
    "Department Spend - P&L",
    "Variance Commentary",
    "Data Sources & Gaps",
    "Validation Checks",
]

MANAGEMENT_REVIEW_SHEETS = [
    "Executive Summary",
    "KPI Scorecard",
    "Income Statement",
    "MRR ARR Waterfall",
    "Pipeline Waterfall",
    "Cash Flow Bridge",
    "Marketing Performance",
    "Variance Commentary",
    "Data Sources & Gaps",
    "Validation Checks",
]

VARIANCE_SHEETS = ["Variance Commentary", "Validation Checks"]

# SMPL MD&A Excel template (Prompt 2) — board Variance Commentary button
MDA_PACKAGE_SHEETS = [
    "Q2 vs Budget",
    "ARR Waterfall",
    "Income Statement",
    "Cash Forecast",
    "Cash Flow Statement",
    "GTM Review",
    "Headcount",
    "Variance Commentary",
    "Risks & Opportunities",
    "Assumptions & Legend",
]

ArtifactKind = Literal[
    "mda_deck_pptx",
    "mda_package_xlsx",
    "management_review_xlsx",
    "variance_commentary_xlsx",
    "board_slide_commentary",
    "copilot_answer",
]


@dataclass(frozen=True)
class ExportArtifactSpec:
    """Maps a deliverable to its API route and structural requirements."""

    artifact: ArtifactKind
    ui_label: str
    endpoint: str
    filename_template: str
    excel_sheets: tuple[str, ...]
    pptx_package_mode: str | None = None
    include_ai_default: bool = False
    notes: str = ""


@dataclass(frozen=True)
class OutputRequirement:
    artifact: ArtifactKind
    title: str
    format: str
    audience: str
    required_sections: tuple[str, ...]
    rules: tuple[str, ...]


BOARD_PLATFORM_EXPORTS: tuple[ExportArtifactSpec, ...] = (
    ExportArtifactSpec(
        artifact="mda_deck_pptx",
        ui_label="MD&A Deck",
        endpoint="/api/v1/export/mda-deck.pptx",
        filename_template="mda_deck_{as_of_period}.pptx",
        excel_sheets=(),
        pptx_package_mode="full_board",
        include_ai_default=True,
        notes="Claude Prompt 5 MD&A deck — never fall back to static /board/exports/*.pptx on API error.",
    ),
    ExportArtifactSpec(
        artifact="mda_package_xlsx",
        ui_label="Variance Commentary",
        endpoint="/api/v1/export/mda-package.xlsx",
        filename_template="SMPL_MDA_Package_{as_of_period}.xlsx",
        excel_sheets=tuple(MDA_PACKAGE_SHEETS),
        include_ai_default=True,
        notes=(
            "SMPL MD&A Excel package (Prompt 2): template tabs refreshed from warehouse "
            "plus Claude variance commentary. NOT month-end-close.xlsx or variance-commentary.xlsx."
        ),
    ),
)

SECONDARY_EXPORTS: tuple[ExportArtifactSpec, ...] = (
    ExportArtifactSpec(
        artifact="management_review_xlsx",
        ui_label="Management review",
        endpoint="/api/v1/export/management-review.xlsx",
        filename_template="management_review_{as_of_period}.xlsx",
        excel_sheets=tuple(MANAGEMENT_REVIEW_SHEETS),
    ),
    ExportArtifactSpec(
        artifact="variance_commentary_xlsx",
        ui_label="Variance commentary only",
        endpoint="/api/v1/export/variance-commentary.xlsx",
        filename_template="variance_commentary_{as_of_period}.xlsx",
        excel_sheets=tuple(VARIANCE_SHEETS),
        notes="Narrow export: Variance Commentary + Validation Checks tabs only.",
    ),
)

EXPORT_ARTIFACTS: tuple[ExportArtifactSpec, ...] = BOARD_PLATFORM_EXPORTS + SECONDARY_EXPORTS


def export_artifact(artifact: ArtifactKind) -> ExportArtifactSpec | None:
    for spec in EXPORT_ARTIFACTS:
        if spec.artifact == artifact:
            return spec
    return None


def board_platform_export(artifact: ArtifactKind) -> ExportArtifactSpec:
    spec = export_artifact(artifact)
    if spec is None or spec not in BOARD_PLATFORM_EXPORTS:
        raise KeyError(f"Not a board platform export artifact: {artifact}")
    return spec


REPORT_OUTPUT_REQUIREMENTS: tuple[OutputRequirement, ...] = (
    OutputRequirement(
        artifact="mda_deck_pptx",
        title="MD&A Board Deck (PowerPoint)",
        format="PPTX — Claude Prompt 5 via /api/v1/export/mda-deck.pptx",
        audience="Board and executive leadership",
        required_sections=(
            "Executive summary scorecard (CM Actual vs Budget vs Forecast)",
            "SaaS MD&A summary narrative (what changed / why / impact)",
            "GTM performance and marketing channel efficiency",
            "Pipeline health, movement, and opportunity drilldown",
            "ARR waterfall and retention/churn context",
            "GAAP revenue and deferred revenue bridge",
            "Cash forecast and operational cash bridge reconciliation",
            "Headcount and department spend",
            "Risks and opportunities",
            "Validation / data quality appendix when enabled",
        ),
        rules=(
            "Evidence-only — every dollar and percentage must trace to warehouse metrics.",
            "Narrative slides use What happened / Why / Impact / Actions structure.",
            "Cash ending balance must tie to cash bridge and balance sheet when data exists.",
            "Do not invent metrics, customers, or variances not present in the bundle.",
            "Board-ready tone: concise, causal, no generic consulting filler.",
        ),
    ),
    OutputRequirement(
        artifact="mda_package_xlsx",
        title="SMPL MD&A Excel Package (board Variance Commentary button)",
        format="XLSX — mda-package.xlsx (SMPL template tabs below)",
        audience="CFO, FP&A, and department owners",
        required_sections=tuple(f"Tab: {name}" for name in MDA_PACKAGE_SHEETS),
        rules=(
            "Refresh all template tabs from build_deck_payload + ts_data + cash_bridge_data.",
            "Variance Commentary tab: Claude Prompt 2 section narratives (what changed / driver / impact).",
            "Numeric cells must be formula-friendly ($M floats), not formatted strings.",
            "Q2 vs Budget uses pl_detail QTD/YTD and budget_qtd_waterfall for ARR rows.",
            "Never fabricate metrics; use warehouse evidence only.",
        ),
    ),
    OutputRequirement(
        artifact="variance_commentary_xlsx",
        title="Variance Commentary Workbook (narrow toolbar export)",
        format="XLSX — variance-commentary.xlsx (2 tabs only)",
        audience="Quick variance-only pull",
        required_sections=tuple(f"Tab: {name}" for name in VARIANCE_SHEETS),
        rules=(
            "Same Variance Commentary row schema as the full MD&A package tab.",
            "Use only when a lightweight variance-only file is requested.",
        ),
    ),
    OutputRequirement(
        artifact="board_slide_commentary",
        title="On-demand slide commentary (Board Platform regenerate)",
        format="JSON narrative per slide key",
        audience="Board Platform UI and export enrichment",
        required_sections=(
            "Single flowing paragraph (4 sentences) for executive takeaway quality",
            "Specific dollars, bps, and period-over-period context",
            "Operational drivers and one forward-looking risk or normalization",
        ),
        rules=(
            "Commentary B quality — not field soup or bullet concatenation.",
            "Use live metrics from the prompt; do not copy example numbers.",
            "No bullet points in regenerate narrative; board-ready prose only.",
        ),
    ),
    OutputRequirement(
        artifact="copilot_answer",
        title="SMPL Copilot Q&A",
        format="Three-section plain-text answer",
        audience="CFO and operators in Board Platform Copilot tab",
        required_sections=(
            "1. Primary driver + variance context",
            "2. Financial and operational root cause",
            "3. Recommended action + board summary sentence",
        ),
        rules=(
            "Search all provided warehouse tables before claiming missing data.",
            "Never invent figures; cite exact amounts from context.",
            "2-3 sentences per section; consistent $ and % formatting.",
        ),
    ),
)


def requirements_for(*artifacts: ArtifactKind) -> list[OutputRequirement]:
    wanted = set(artifacts)
    return [req for req in REPORT_OUTPUT_REQUIREMENTS if req.artifact in wanted]


def requirements_prompt_block(*artifacts: ArtifactKind) -> str:
    """Markdown-ish block for Anthropic system/user prompts."""
    selected = requirements_for(*artifacts) if artifacts else list(REPORT_OUTPUT_REQUIREMENTS)
    if not selected:
        return ""
    lines = ["OUTPUT REQUIREMENTS (minimum deliverable standards):"]
    for req in selected:
        lines.append(f"\n## {req.title}")
        lines.append(f"Format: {req.format}")
        lines.append(f"Audience: {req.audience}")
        lines.append("Required sections:")
        for section in req.required_sections:
            lines.append(f"  - {section}")
        lines.append("Rules:")
        for rule in req.rules:
            lines.append(f"  - {rule}")
    return "\n".join(lines)


def monthly_close_requirements_prompt() -> str:
    """Full requirements block for month-end report generation (deck + MD&A package)."""
    return requirements_prompt_block("mda_deck_pptx", "mda_package_xlsx", "board_slide_commentary")
