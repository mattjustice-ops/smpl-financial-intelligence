# MD&A package schema v2

The export has two stages:

1. The **package builder** reads approved commentary and ledger amounts from the platform and writes one JSON package.
2. The **renderer** (`reference/build_mdna_workbook.py`, generalized) turns the package into the workbook. It never reads the database and never writes sentences.

`reference/mdna_package.json` is a v1 package. It renders the reference workbook exactly. v2 keeps every v1 field and adds the fields marked **new**. Those fields replace values that the v1 renderer hard-codes for the SMPL fixture: line IDs, month names and the thousands unit.

## Conventions

- **Amounts:** integer cents, in the line's reported sign (revenue and costs positive).
- **Shown amounts** (`varShown`, `drivers[].shown`, `summary.cited[].shown`): rounded at the package precision. They are kept in cents (a shown 23.5k is `2350000`).
- **Labels:** final display strings. The renderer does not change them.

## Top level

| Field | Type | Notes |
|---|---|---|
| `schemaVersion` **new** | `2` | |
| `stamp` | object | See Stamp |
| `comparisons` | array | Only comparisons with data. A comparison with no data is listed in `notIncluded` and gets no tab |
| `notIncluded` **new** | array of `{label, reason}` | e.g. `{"label": "vs Forecast (month)", "reason": "No forecast version loaded for Jun 2026"}`, or `{"label": "Labor bridge", "reason": "No workforce data loaded"}`. Shown on the Cover |
| `labor` | array (may be empty) | See Labor. Empty means no Labor bridge tab |
| `watch` | object | `items` may be empty |
| `scoring` | object or `null` | `null` when no impacts were noted at the prior close |

## Stamp

v1 fields: `packageId`, `entity`, `book`, `currency`, `snapshot`, `period` (e.g. "Jun 2026"), `generatedAt`, `generatedBy`, `contentHash`, `status`, `approver {by, at}`.

| Field | Notes |
|---|---|
| `status` | `"Approved"` when every comparison in the package is approved, otherwise `"Draft"`. A draft can still be exported, but the renderer marks it everywhere (see the prompt) |
| `approver` | `null` for a draft |
| `periodLong` **new** | "June 2026", used in titles |
| `entityName` **new** | Display name, e.g. "SMPL Demo Co" |
| `precision` **new** | The divisor converts cents to displayed units. **Default: whole dollars**, `{"unitLabel": "USD", "divisor": 100, "decimals": 0}`, which is the precision reviewers approve the commentary at in the app. The other option is `{"unitLabel": "USD thousands", "divisor": 100000, "decimals": 1}`; the reference fixture uses it. Cells and paragraphs always share one precision, and the tie checks run at it |
| `dataNote` **new** | Optional line for the Cover (the reference says "Synthetic fixture…"). Omit for customer data |

## Comparison

v1 fields: `key`, `short`, `tab`, `label`, `cid`, `curLabel`, `cmpLabel`, `bsLabels`, `views`, `walks`, `checks`, `allOk`, `approval`, `kpis`, `summary`.

| Field | Notes |
|---|---|
| `tab` | The sheet name, at most 31 characters |
| `bsLabels` | `[current, comparison]` balance-sheet dates. Balances are **point in time**: the end of the current period vs the end of the comparison point. QoQ compares the end of the prior quarter; YTD compares the prior year end. Never sum balances across months |
| `approval` | `{status, by, at, reviewed, inScope}`. In a draft, `status` is "Not approved" and `by`/`at` are `null` |
| `views` | `{IS, MP, GL, BS, CF}`, in that order. Each view is `{label, rows, na}`. When a view can't exist for this comparison (a plan with no balance sheet), `rows` is `null` and `na` says why |
| `walks` | `{IS: walk, MP: walk}`. A walk is `{rootNid` **new**`, start, end, steps: [{nid, label, coef, step}]}`. The steps are the root's formula flattened into statement lines (spec §19.5 rule 7), so `start + Σ step = end` exactly |
| `kpis` | Each entry is `{view` **new**`, nid` **new**`, role` **new**`, label, cur, cmp, var, fu}`. `role` is one of `revenue`, `gross_profit`, `opex`, `operating_income`, `net_income` or `contribution`. Include a KPI only if the statement has that line. The renderer adds gross margin when both `revenue` and `gross_profit` are present |
| `checks` | `[{id` **new** `("T22"…"T27"), t, ok, na}]` |
| `summary` | `{text, source` **new** `("AI" or "Template"), ok, cited: [{label, shown}], sum, target}`. See the prompt for the fallback |

## Row (each entry in `views.X.rows`)

v1 fields: `nid`, `label`, `level`, `style`, `kind`, `sign`, `children`, `cur`, `cmp`, `var`, `varShown`, `fu`, `text`, `source`, `drivers`, `lineBased`, `inScope`, `reviewedBy`, `reviewedAt`, `impact`, `driversOk`, `rollOk`, `paraOk`.

| Field | Notes |
|---|---|
| `level` | Depth in the rollup tree: 0 = statement line. v1 only used 0 and 1. v2 allows any depth; the renderer caps the Excel outline at 7 |
| `role` **new** | `statement`, `child`, `subtotal`, `total`, `plug` or `no_dimension`. Sets the row style; replaces guessing from `style` |
| `style` | Kept for v1: `"strong"` for subtotals, `"total"` for totals, `"leaf"` for detail rows, `""` for other statement lines |
| `kind` | `"leaf"`: amounts are ledger constants. `"sum"` or `"formula"`: amounts are worksheet formulas over `children` |
| `children` | `[[nid, coef], …]` for a `sum` or `formula` row. Every child is also a row in the same view, at any depth |
| `sign` | `INCOME` (up is favorable, and cash-flow inflows), `EXPENSE` (up is unfavorable) or `NEUTRAL` (balance-sheet lines and ending cash: no F/U) |
| `label` | The display label: at most two segments ("Engineering · Cloud Hosting COGS"). The full path goes in `path` |
| `path` **new** | The full tree path, used for the cell comment |
| `cur`, `cmp` | Balance-sheet rows and ending cash: balances at the two `bsLabels` dates. Every other row: the flow over each period |
| `text` | The approved paragraph, rendered at the package precision (spec §19.8 tokens → displayed values). No cents and no "$" |
| `source` | `Template`, `AI` or `Edited` |
| `drivers` | `[{label, exact, shown}]`: the rows the paragraph cites, plus Other. `Σ exact = var` and `Σ shown = varShown` |
| `impact` | `{nextTotal, text}` or `null` |
| `reviewedBy`, `reviewedAt` | Initials and date, or `null` |
| `driversOk`, `rollOk`, `paraOk` | T22, T23 and T26 for this line |

## Labor (each entry in `labor`)

v1 fields: `key`, `title`, `company {start, end, bars}`, `byDept [{dept, name, start, end, bars}]`, `ties`.

| Field | Notes |
|---|---|
| `key` | The comparison key this bridge belongs to (e.g. `MOM`, `BUD_M`). Replaces the renderer's hard-coded order |
| `compNid` **new** | The GL row for total compensation in that comparison tab. Replaces `GL.COMP` |
| `byDept[].nid` **new** | The GL row for that department's compensation. Replaces `GL.6000.<dept>` |
| `startLabel`, `endLabel`, `ledgerLabel` **new** | e.g. "May 2026 actual (compensation)", "Jun 2026 actual (bridge)", "Jun 2026 compensation (ledger)" |
