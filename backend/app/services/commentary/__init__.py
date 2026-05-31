"""AI-generated CFO commentary service."""

from app.services.commentary.openai_client import (
    CommentaryLLMClient,
    LLMError,
    OpenAICommentaryClient,
)
from app.services.commentary.prompts import (
    SYSTEM_PROMPT,
    build_user_prompt,
    output_schema_json,
)
from app.services.commentary.schemas import (
    CommentaryInputs,
    CommentaryOutput,
    CommentarySection,
    Citation,
    CustomerMovementSummary,
    DataGap,
    FollowupQuestion,
    KpiTrend,
    MrrWaterfallSummary,
    PipelineChange,
    QuotaAttainment,
    RevenueForecastInput,
    RiskOpportunity,
    SalesEfficiencyInput,
    BookingsForecastInput,
    CashCollectionsForecastInput,
    VarianceRow,
)
from app.services.commentary.service import generate_commentary

__all__ = [
    "CommentaryInputs",
    "CommentaryLLMClient",
    "CommentaryOutput",
    "CommentarySection",
    "Citation",
    "CustomerMovementSummary",
    "DataGap",
    "FollowupQuestion",
    "KpiTrend",
    "LLMError",
    "MrrWaterfallSummary",
    "OpenAICommentaryClient",
    "PipelineChange",
    "QuotaAttainment",
    "RevenueForecastInput",
    "RiskOpportunity",
    "SalesEfficiencyInput",
    "BookingsForecastInput",
    "CashCollectionsForecastInput",
    "SYSTEM_PROMPT",
    "VarianceRow",
    "build_user_prompt",
    "generate_commentary",
    "output_schema_json",
]
