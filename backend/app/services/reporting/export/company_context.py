"""Company strategic context for board / MD&A commentary (operational finance platform)."""

from __future__ import annotations

COMPANY_NAME = "SMPL"
COMPANY_TAGLINE = "We make finance simple"

COMPANY_PROFILE = """
Company: SMPL — We make finance simple.

SMPL is a mid-market B2B SaaS platform — workflow automation and operational intelligence
for finance and revenue organizations.

Product: Centralizes financial planning, operational reporting, GTM forecasting, and
executive decision-making in one operational finance intelligence layer.

Market: Modern SaaS FP&A and operational planning; customers moving off spreadsheets
and fragmented BI toward integrated operational finance.

Competitive set: Anaplan (enterprise complexity), Pigment (collaborative planning),
Workday Adaptive (FP&A + ERP), Mosaic (mid-market strategic finance), Cube
(spreadsheet-native FP&A), Abacum (SaaS operational finance).

Differentiation: Connect operational GTM data, SaaS revenue mechanics, pipeline
forecasting, cash forecasting, executive commentary, and board reporting in one layer.
SaaS-native metrics, executive storytelling, AI-assisted finance workflows,
operational drilldowns, integrated finance + GTM visibility.

Strengths: Integrated SaaS operational finance model; ARR/MRR forecasting; deep GTM
integration; modern executive reporting; AI variance commentary; cash tied to drivers.

Weaknesses: Early product maturity; source-system data quality dependency; forecast
accuracy still improving; limited cohort depth; workflow automation evolving.

Opportunities: AI-enabled finance tools demand; SaaS CFO integrated reporting; GTM
finance operationalization; faster close cycles; mid-market spreadsheet displacement.

Threats: Entrenched enterprise planning vendors; BI expanding into planning; ERP
reporting improvements; integration complexity; SaaS budget pressure in downturns.

Strategic priorities:
1. Improve forecast accuracy
2. Increase enterprise ARR growth
3. Improve pipeline efficiency
4. Maintain liquidity and cash conversion
5. Reduce close cycle timing
6. Improve GTM visibility
7. Scale board reporting automation
8. Increase operational leverage

Favorable themes (when supported by data): enterprise expansion ARR; paid search
efficiency; healthy pipeline/spend; collections via annual upfront billings;
improving forecast accuracy; GTM visibility.

Unfavorable themes (when supported by data): elevated SMB churn; pipeline slippage;
engineering hiring ahead of plan; vendor spend discipline; lower SMB forecast confidence.

Leadership posture: Prioritize predictable ARR, pipeline quality, operational
efficiency, forecast accuracy, cash discipline, executive visibility. Will invest in
enterprise GTM and accept short-term EBITDA pressure when pipeline efficiency,
expansion ARR, and forecast confidence remain healthy.
""".strip()


COMPETITOR_TABLE = [
    ["Anaplan", "Enterprise planning / complexity"],
    ["Pigment", "Modern collaborative planning"],
    ["Workday Adaptive Planning", "FP&A + ERP integration"],
    ["Mosaic", "Mid-market strategic finance"],
    ["Cube", "Spreadsheet-native FP&A"],
    ["Abacum", "SaaS operational finance"],
]


def strategic_context_for_prompt() -> str:
    return COMPANY_PROFILE
