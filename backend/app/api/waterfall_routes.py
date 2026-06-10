"""Expandable waterfall APIs."""



from __future__ import annotations



import traceback

import uuid



from fastapi import APIRouter, Depends, HTTPException, Query

from pydantic import ValidationError

from sqlalchemy.orm import Session



from app.api.reporting_params import dashboard_params, enrich_reporting_params

from app.db.session import get_db

from decimal import Decimal



from app.services.dashboard.pipeline_opportunity_drilldown_service import pipeline_drilldown

from app.services.dashboard.cash_flow_gl_drilldown_service import cash_flow_drilldown

from app.services.dashboard.schemas import (

    CashFlowDrilldownResponse,

    PipelineDrilldownResponse,

    WaterfallAttributionRow,

    WaterfallResponse,

)

from app.services.dashboard.waterfall_service import waterfall_response

from app.services.organizations import get_organization_or_404



waterfall_router = APIRouter(prefix="/waterfalls", tags=["waterfalls"])





def _params(

    scenario: str,

    start_period: str,

    end_period: str,

    period: str | None,

    quarter: str | None,

    fiscal_year: str | None,

    waterfall_type: str | None,

    marketing_channel: str | None,

    region: str | None,

    segment: str | None,

    owner: str | None,

) -> dict:

    return dashboard_params(scenario, start_period, end_period, period, quarter, fiscal_year, waterfall_type, marketing_channel, region, segment, owner)





def _response(

    waterfall_name: str,

    organization_id: uuid.UUID,

    db: Session,

    *,

    as_of_period: str | None = None,

    **params,

) -> WaterfallResponse:

    get_organization_or_404(db, organization_id)

    params = enrich_reporting_params(db, organization_id, params, as_of_period=as_of_period)

    return waterfall_response(db, organization_id, waterfall_name=waterfall_name, **params)





def _attribution(

    waterfall_name: str,

    organization_id: uuid.UUID,

    db: Session,

    *,

    as_of_period: str | None = None,

    **params,

) -> list[WaterfallAttributionRow]:

    return _response(waterfall_name, organization_id, db, as_of_period=as_of_period, **params).attribution





def _bind_as_of(

    db: Session,

    organization_id: uuid.UUID,

    *,

    scenario: str,

    period: str,

    as_of_period: str | None,

) -> None:

    enrich_reporting_params(

        db,

        organization_id,

        {"scenario": scenario, "start_period": period, "end_period": period},

        as_of_period=as_of_period,

    )





def route_params(

    scenario: str = Query("Combined"),

    start_period: str = Query(...),

    end_period: str = Query(...),

    period: str | None = Query(None),

    quarter: str | None = Query(None),

    fiscal_year: str | None = Query(None),

    waterfall_type: str | None = Query(None),

    marketing_channel: str | None = Query(None),

    region: str | None = Query(None),

    segment: str | None = Query(None),

    owner: str | None = Query(None),

) -> dict:

    return _params(scenario, start_period, end_period, period, quarter, fiscal_year, waterfall_type, marketing_channel, region, segment, owner)





@waterfall_router.get("/arr", response_model=WaterfallResponse)

def arr(

    organization_id: uuid.UUID = Query(...),

    as_of_period: str | None = Query(None, description="Close month for Combined (YYYY-MM)"),

    params: dict = Depends(route_params),

    db: Session = Depends(get_db),

) -> WaterfallResponse:

    return _response("arr", organization_id, db, as_of_period=as_of_period, **params)





@waterfall_router.get("/arr/attribution", response_model=list[WaterfallAttributionRow])

def arr_attr(

    organization_id: uuid.UUID = Query(...),

    as_of_period: str | None = Query(None),

    params: dict = Depends(route_params),

    db: Session = Depends(get_db),

) -> list[WaterfallAttributionRow]:

    return _attribution("arr", organization_id, db, as_of_period=as_of_period, **params)





@waterfall_router.get("/pipeline", response_model=WaterfallResponse)

def pipeline(

    organization_id: uuid.UUID = Query(...),

    as_of_period: str | None = Query(None),

    params: dict = Depends(route_params),

    db: Session = Depends(get_db),

) -> WaterfallResponse:

    return _response("pipeline", organization_id, db, as_of_period=as_of_period, **params)





@waterfall_router.get("/pipeline/attribution", response_model=list[WaterfallAttributionRow])

def pipeline_attr(

    organization_id: uuid.UUID = Query(...),

    as_of_period: str | None = Query(None),

    params: dict = Depends(route_params),

    db: Session = Depends(get_db),

) -> list[WaterfallAttributionRow]:

    return _attribution("pipeline", organization_id, db, as_of_period=as_of_period, **params)





@waterfall_router.get("/pipeline/drilldown", response_model=PipelineDrilldownResponse)

def pipeline_drilldown_route(

    organization_id: uuid.UUID = Query(...),

    scenario: str = Query("Combined"),

    period: str = Query(..., description="YYYY-MM period for the selected cell"),

    waterfall_type: str = Query(..., description="pipeline_created, closed_won, closed_lost, slipped_pipeline"),

    expected_amount: Decimal | None = Query(None),

    marketing_channel: str | None = Query(None),

    region: str | None = Query(None),

    segment: str | None = Query(None),

    owner: str | None = Query(None),

    as_of_period: str | None = Query(None, description="Close month for Combined (YYYY-MM)"),

    db: Session = Depends(get_db),

) -> PipelineDrilldownResponse:

    get_organization_or_404(db, organization_id)

    _bind_as_of(db, organization_id, scenario=scenario, period=period, as_of_period=as_of_period)

    return pipeline_drilldown(

        db,

        organization_id,

        scenario=scenario,

        period=period,

        waterfall_type=waterfall_type,

        expected_amount=expected_amount,

        marketing_channel=marketing_channel,

        region=region,

        segment=segment,

        owner=owner,

    )





@waterfall_router.get("/deferred-revenue", response_model=WaterfallResponse)

def deferred_revenue(

    organization_id: uuid.UUID = Query(...),

    as_of_period: str | None = Query(None),

    params: dict = Depends(route_params),

    db: Session = Depends(get_db),

) -> WaterfallResponse:

    try:

        result = _response("deferred_revenue", organization_id, db, as_of_period=as_of_period, **params)

        result.model_dump(mode="json")

        return result

    except ValidationError as exc:

        raise HTTPException(status_code=500, detail=f"deferred_revenue response validation: {exc.errors()}") from exc

    except HTTPException:

        raise

    except Exception as exc:

        raise HTTPException(

            status_code=500,

            detail=f"deferred_revenue failed: {type(exc).__name__}: {exc}\n{traceback.format_exc()[-4000:]}",

        ) from exc





@waterfall_router.get("/deferred-revenue/attribution", response_model=list[WaterfallAttributionRow])

def deferred_revenue_attr(

    organization_id: uuid.UUID = Query(...),

    as_of_period: str | None = Query(None),

    params: dict = Depends(route_params),

    db: Session = Depends(get_db),

) -> list[WaterfallAttributionRow]:

    return _attribution("deferred_revenue", organization_id, db, as_of_period=as_of_period, **params)





@waterfall_router.get("/cash-flow", response_model=WaterfallResponse)

def cash_flow(

    organization_id: uuid.UUID = Query(...),

    as_of_period: str | None = Query(None),

    params: dict = Depends(route_params),

    db: Session = Depends(get_db),

) -> WaterfallResponse:

    return _response("cash_flow", organization_id, db, as_of_period=as_of_period, **params)





@waterfall_router.get("/cash-flow/attribution", response_model=list[WaterfallAttributionRow])

def cash_flow_attr(

    organization_id: uuid.UUID = Query(...),

    as_of_period: str | None = Query(None),

    params: dict = Depends(route_params),

    db: Session = Depends(get_db),

) -> list[WaterfallAttributionRow]:

    return _attribution("cash_flow", organization_id, db, as_of_period=as_of_period, **params)





@waterfall_router.get("/cash-flow/drilldown", response_model=CashFlowDrilldownResponse)

def cash_flow_drilldown_route(

    organization_id: uuid.UUID = Query(...),

    scenario: str = Query("Combined"),

    period: str = Query(..., description="YYYY-MM period for the selected cell"),

    waterfall_type: str = Query(..., description="cash_collections, payroll_cash_out, vendor_cash_out, etc."),

    expected_amount: Decimal | None = Query(None),

    as_of_period: str | None = Query(None, description="Close month for Combined (YYYY-MM)"),

    db: Session = Depends(get_db),

) -> CashFlowDrilldownResponse:

    get_organization_or_404(db, organization_id)

    _bind_as_of(db, organization_id, scenario=scenario, period=period, as_of_period=as_of_period)

    return cash_flow_drilldown(

        db,

        organization_id,

        scenario=scenario,

        period=period,

        waterfall_type=waterfall_type,

        expected_amount=expected_amount,

    )

