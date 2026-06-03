# HubSpot setup for /request-quote

When a quote form is submitted, the server creates or updates:

1. **Contact** — standard HubSpot fields
2. **Company** — name, domain, plus a full summary in **Description**
3. **Deal** — in pipeline **SMPL Inbound Sales**, with summary in **Description**

Custom `smpl_*` properties are applied when they exist in HubSpot. If they do not exist yet, the submission still succeeds and all details are stored in the company/deal **Description** fields.

## 1. Vercel environment variables

In **Vercel → Project → Settings → Environment Variables**:

| Variable | Value |
|----------|--------|
| `HUBSPOT_PRIVATE_APP_TOKEN` | Your `pat-...` token |
| `HUBSPOT_PIPELINE_NAME` | `SMPL Inbound Sales` |

Redeploy after saving.

## 2. Private app scopes (required)

In HubSpot → Settings → Integrations → Private Apps → your app → **Scopes**:

- `crm.objects.contacts.read`
- `crm.objects.contacts.write`
- `crm.objects.companies.read`
- `crm.objects.companies.write`
- `crm.objects.deals.read`
- `crm.objects.deals.write`
- `crm.schemas.contacts.read`
- `crm.schemas.companies.read`
- `crm.schemas.deals.read`

Save and regenerate the token if scopes changed, then update Vercel.

## 3. Health check

After deploy, open:

```
https://smpl-financial-intelligence.vercel.app/api/request-quote/hubspot-health
```

Expected:

```json
{
  "tokenConfigured": true,
  "pipelineFound": true,
  "pipelineName": "SMPL Inbound Sales",
  "pipelineLabel": "SMPL Inbound Sales"
}
```

If `tokenConfigured` is false → add `HUBSPOT_PRIVATE_APP_TOKEN` in Vercel and redeploy.

If `pipelineFound` is false → create the pipeline in HubSpot or fix `HUBSPOT_PIPELINE_NAME`.

## 4. Optional custom properties

Create these in HubSpot if you want structured fields instead of description-only:

**Company:** `smpl_arr_range`, `smpl_employee_count`, `smpl_finance_team_size`, `smpl_company_stage`, `smpl_current_erp`, `smpl_current_crm`, `smpl_current_billing_system`, `smpl_current_hris`, `smpl_current_planning_tool`, `smpl_data_reliability`

**Deal:** `smpl_requested_modules`, `smpl_business_needs`, `smpl_biggest_challenge`, `smpl_current_solution`, `smpl_expected_users`, `smpl_implementation_timeline`, `smpl_deployment_preference`, `smpl_budget_range`, `smpl_lead_score`, `smpl_recommended_package`

## 5. Debug a failed submission

In the browser DevTools → **Network** tab → submit the form → open the `request-quote` response.

Look at `hubspot`:

- `ok: false` → read `error` (token, pipeline, scopes, etc.)
- `ok: true` → check Contacts, Companies, and Deals in HubSpot; search by submitter email or company name
