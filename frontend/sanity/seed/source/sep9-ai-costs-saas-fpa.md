# Deliverables

**1. URL slug:** `ai-costs-saas-fpa`

**2. SEO title (53 chars):** How AI Changes SaaS Cost Structure and FP&A | SMPL.ai

**3. Meta description:** AI turns software delivery into a variable cost. How FP&A should model inference in COGS, forecast gross margin, and connect usage to the financial plan.

**4. H1:** AI Is Changing the Cost Structure FP&A Has to Understand

---

# Article

AI is not only changing what software does. It is changing what software costs to deliver, and that lands in the P&L before it appears in anyone's strategy deck.

Most discussion of AI in software concerns capability, productivity, and competitive positioning. Finance has a different question underneath it. What happens to the economics of a business when every additional customer action can trigger incremental compute?

That question has no single answer, but it has a structure, and Finance teams that learn it early fare better than those who meet it in a gross margin miss.

## How does AI change the traditional SaaS cost model?

AI makes delivery cost move with customer activity rather than sit largely fixed.

Classic software was attractive because the marginal cost of serving one more unit of usage was close to nothing. That was never literally true, since hosting, storage, support, and third-party APIs have always cost money. But the link between what a customer did in the product and what it cost to serve them was loose. A user opening a few more screens did not move the infrastructure bill measurably.

With AI in the product, that link tightens. A user asking an agent to run another multi-step workflow consumes compute, billed per token, every time.

The reported margin data shows both the size of the gap and its direction. ICONIQ's State of AI 2026 report, "The Builder's Economy," published in July 2026 from a survey of roughly 300 software executives, puts AI product gross margins at 45 percent in 2025, with a projected 53 percent in 2026 and 59 percent in 2027. Bessemer Venture Partners, in its February 2026 pricing playbook, describes AI companies operating at 50 to 60 percent gross margins against 80 to 90 percent for traditional SaaS.

Two things are worth drawing out. The level sits well below software norms, which is what most commentary focuses on. The trajectory climbs, which Finance should care about more, because it indicates a variable being actively managed rather than a fixed penalty. ICONIQ reinforces that reading by separating cohorts: high-growth companies are projected at 64 percent gross margin in 2027 against 58 percent for the rest of the sample. A six point spread inside the same year suggests decisions, not destiny.

## Which kind of AI company are you?

Before applying those benchmarks, work out which situation you are in, because the 50 to 60 percent band describes products where the model is the product, not a mature SaaS application that added a summarization button.

**AI-augmented** products use AI as a convenience layer, occasionally and often optionally. Incremental cost is real but small against revenue, and a percentage-of-revenue assumption may still be adequate. **AI-enabled** products use AI as a core feature several times a week or more, where cost is material and varies meaningfully between customers. **AI-native** products are the model itself, where nearly every interaction is an inference call and AI cost of delivery deserves its own line.

The first FP&A question is not how to model AI costs. It is how material they are and on what trajectory. If AI infrastructure is 0.4 percent of revenue and growing slowly, an elaborate driver tree wastes your time. If it is 6 percent and doubling annually, it is the most important item on your list.

## What actually drives AI cost?

Finance does not need the architecture. It needs the drivers.

**Tokens** are billed on input and output, usually at different rates, with output typically more expensive, so a product sending long prompts and returning short answers has a very different cost shape from one generating long documents. **Context** size compounds this, because attaching customer history or a financial dataset increases input tokens on every call. **Model selection** can move unit cost by an order of magnitude, which makes routing routine requests to smaller models a genuine margin lever.

**Agentic workflows and frequency** are what Finance most often misses. One user action can trigger retrieval, reasoning, validation, a tool call, a retry, and a summarization, so one customer action does not equal one AI call, and the multiplier is commonly several times over. A feature used twice a month and an agent running continuously are not the same business.

**Supporting infrastructure** including vector databases, embeddings, storage, warehouse queries, GPU capacity, and observability all scales with activity in ways traditional hosting did not.

## How does customer activity become gross margin?

The chain Finance needs to make explicit runs like this:

**Customer activity → AI consumption → infrastructure cost → cost of delivery → gross margin → pricing → unit economics → forecast**

A workable driver tree underneath it:

Customers → active AI users per customer → AI workflows per user per month → model calls per workflow → tokens per call → cost per token by model → infrastructure cost → customer-level cost of delivery → gross margin

Your tree will differ. What matters is that Finance can name every link between what customers do and what the business earns, because each holds an assumption that in most companies has never been written down.

A careful word on accounting. Whether a given AI cost belongs in cost of goods sold, which most software companies report as cost of revenue, depends on the nature of the cost, how the service is delivered, your accounting policy, and applicable guidance. Inference and infrastructure costs directly associated with delivering a customer-facing service are commonly evaluated within cost of revenue, while model training, research, and internal tooling often sit elsewhere. Work the classification through with your accounting team rather than applying a rule of thumb, because where you draw that line materially changes reported gross margin. Where this article refers to AI COGS, it means whichever AI costs your own policy places above the gross margin line.

## What does the math actually look like?

All figures below are hypothetical, chosen for arithmetic that is easy to follow. They are not benchmarks, and the blended token rate is a placeholder rather than any provider's published price.

A company has 1,000 customers and $20M ARR. In the baseline, 30 percent of customers have adopted the AI features, each adopting customer has 8 active AI users running 40 workflows a month, each workflow makes 6 model calls because the workflows are agentic, and each call consumes 8,000 tokens across input and output.

Now change two assumptions, neither of which is revenue. Adoption rises from 30 to 60 percent as the feature proves itself, and workflows per user climb from 40 to 70 as customers grow more comfortable.

| Driver | Baseline | Higher adoption |
|---|---|---|
| Customers | 1,000 | 1,000 |
| AI adoption rate | 30% | 60% |
| Adopting customers | 300 | 600 |
| Active AI users per adopting customer | 8 | 8 |
| Total active AI users | 2,400 | 4,800 |
| Workflows per user per month | 40 | 70 |
| Model calls per workflow | 6 | 6 |
| Tokens per call | 8,000 | 8,000 |
| Tokens per month | 4.608 billion | 16.128 billion |
| Blended cost per million tokens (illustrative) | $3.00 | $3.00 |
| AI cost per month | $13,824 | $48,384 |
| AI cost per year | $165,888 | $580,608 |
| AI cost as a share of $20M ARR | 0.83% | 2.90% |

AI COGS more than tripled. ARR did not move at all. A forecast scaling AI cost as a percentage of revenue would have missed this entirely, because what changed was customer behavior, not billings.

## Why can two customers with the same ARR have different economics?

Two customers each pay $50,000. One uses the AI features lightly. The other has rolled them out across three teams and runs agentic workflows daily. Identical ARR, materially different gross profit.

In traditional SaaS, ARR was a fair proxy for customer value because cost to serve barely varied between accounts. In an AI-enabled product that proxy weakens, and retention, expansion, and pricing decisions made on ARR alone can quietly favor your least profitable customers.

This does not mean every company needs customer-level AI profitability reporting. It means knowing whether the variance between customers is material. If your heaviest decile consumes many times the median, that is a pricing question rather than a reporting curiosity.

## Why does percentage-of-revenue forecasting break for AI COGS?

Because the composition of the cost base is shifting, and a revenue ratio cannot see that.

ICONIQ's July 2026 report tracks how AI product costs are distributed as a product matures. Model inference accounts for 20 percent of AI product cost before launch and 23 percent once the product is generally available and operating at scale. Over the same progression, talent falls from 32 percent of cost to 26 percent.

Note the denominator carefully. These are shares of AI product cost, not shares of revenue and not a gross margin ratio. The finding is about mix.

That mix shift is the substantive point for Finance. As an AI product matures, the cost base rotates away from engineering payroll, which is fixed in the short run and budgeted by headcount, toward inference, which is variable and budgeted by usage. The cost structure becomes more demand-sensitive over time rather than less.

A percentage-of-revenue assumption carries an implicit belief that cost tracks billings. In an AI product, cost tracks usage, and under flat subscription pricing those two are free to diverge, as the worked example shows.

Questions a driver-based forecast should answer:

- What happens if AI adoption grows faster than revenue?
- What if users shift toward more expensive models or heavier features?
- What if average tokens per workflow rise as the product becomes more capable?
- What if a provider changes pricing, or engineering halves the calls per workflow?
- What if usage is far more concentrated in a few accounts than we assumed?

The model does not need to be precise. It needs to expose assumptions clearly enough that someone can argue with them.

## If inference is getting cheaper, why is the cost line growing?

Because falling prices apply to a fixed level of capability, and products rarely hold capability fixed.

Andreessen Horowitz documented the trend in its 2024 "LLMflation" analysis, finding that for a model of equivalent performance, inference cost was falling roughly 10x per year, with a GPT-3-class model dropping from about $60 per million tokens in 2021 to roughly $0.06 by late 2024. ICONIQ's 2026 survey points the same way, with two-thirds of companies reporting improved per-query unit economics they attribute to inference cost management, model routing, and scale leverage.

Set that against the mix shift above and the resolution is straightforward. The qualifier "of equivalent performance" does considerable work, because almost nobody ships equivalent performance year over year. Teams take the price decline and spend it on capability: longer context, retrieval, self-critique passes, more agent calls per workflow. Unit prices fall while units consumed rise.

Do not plan on falling model prices repairing gross margin by themselves, because your own product roadmap is the main thing working against that.

## How should AI economics change pricing and packaging?

If usage drives cost, pricing has to acknowledge usage somewhere in its structure.

The market is already moving. ICONIQ's July 2026 data shows consumption-based pricing rising from 35 to 42 percent of companies within six months, outcome-based pricing from 18 to 23 percent, and companies blending an average of 1.7 pricing models rather than choosing one.

GitHub Copilot is a detailed public example of that blending. On 1 June 2026, Copilot moved from premium request units to usage-based billing measured in GitHub AI Credits, where one credit equals one cent, with consumption calculated from input, output, and cached tokens priced per model. Base plan prices did not change. Each plan carries a monthly credit allotment: Pro at $10 with 1,500 credits, Pro+ at $39 with 7,000, Max at $100 with 20,000, Business at $19 per user with 1,900, and Enterprise at $39 per user with 3,900. Credits do not roll over, usage beyond the allotment is purchased as overage, and code completions and next edit suggestions do not consume credits.

This is not a switch to pure usage pricing. It is subscription, plus a bundled consumption allowance, plus metered overage, which is precisely the hybrid structure most software companies end up considering. One detail deserves Finance attention: individual plans include a variable flex allotment GitHub says it will adjust as model economics change, while Business and Enterprise plans have none. A pricing mechanism built to be adjusted over time is a reasonable response to a cost base that is hard to size in advance, which is exactly what agentic workloads create.

There is no universally correct structure. Options run from bundling AI into the base subscription, through fair-use limits, tiered access, credit allotments, premium modules, overages, and pure consumption pricing, each trading customer predictability against cost alignment. Finance's contribution is ensuring the decision reflects customer value, usage behavior, cost to serve, and willingness to pay together. If AI usage materially changes cost to serve, Finance needs visibility into that usage before the pricing decision, not after gross margin misses plan.

## How should AI COGS enter the budget and forecast?

Annual planning usually breaks here, because AI infrastructure gets handled as an Engineering line item rather than a business model assumption.

Take a plan built on 30 percent customer growth. If AI adoption per customer also rises 50 percent, a model scaling AI cost with customer count or revenue will understate infrastructure materially. The error is not arithmetic. An operational assumption never entered the financial model.

The budget needs a traceable path from customer growth, to AI adoption, to usage per customer, to model consumption, to infrastructure cost, to gross margin, to cash, with an owner for each link. Then run scenarios: adoption above plan, customers doubling activity, provider pricing changes, migration to more expensive models, engineering cutting calls per workflow, usage limits or credits. Most useful is a gross margin floor scenario answering what maximum AI cost structure the business can carry while holding target margin. That number tells Product and Engineering what they are designing against, which is more actionable than a request to be efficient.

This is also where the organizational gap shows up, because decisions that move gross margin get made in product planning meetings by people not looking at a P&L: model selection, context size, retry logic, caching strategy, agent steps per workflow. Engineering does not need to become Finance, and Finance does not need to become Engineering, but someone has to connect the two views. It is the same problem that appears whenever [small differences upstream compound into large financial differences downstream](/blog/data-bullwhip-effect-finance), solved the same way, by making the causal chain visible to everyone who affects it.

## Where does AI FinOps end and FP&A begin?

A category of tooling and practice has grown around monitoring AI usage, optimizing model costs, routing workloads, and observing inference economics. It is genuinely useful once AI spend becomes material, and it answers a different question than Finance is asking.

AI FinOps asks how efficiently the company consumes AI infrastructure. FP&A asks what that consumption means for revenue, margin, pricing, cash, and the operating plan.

Those are complementary. AI FinOps helps control the cost. FP&A translates it into the financial model, connects it to pricing and customer strategy, and explains the result to a board.

## What should FP&A teams do now?

1. **Identify the material AI cost drivers** before modeling anything, and establish where usage and cost data live and who owns them.
2. **Connect usage to customers or products where practical**, so AI infrastructure stops being one opaque monthly number.
3. **Build a driver-based forecast** connecting product activity to cost, even approximately.
4. **Model gross margin sensitivity** to find where the economics break, not only where they sit today.
5. **Review pricing against actual usage** to test whether ARR still describes customer economics.
6. **Preserve your assumptions and compare them against outcomes.** Over several quarters you learn whether your usage assumptions run optimistic or conservative, which is worth more than any single forecast.
7. **Put AI economics in the operating plan** rather than treating it as an Engineering afterthought.

Whether your current stack can carry that work is a separate question, and most of it depends on how well the system joins product usage to financial results. We compared how the main categories of tooling handle that in [our guide to FP&A software for SaaS companies](/blog/best-fpa-software-saas-companies).

## Why does the financial model have to reflect how the product works?

The broader shift is not really about AI. Finance increasingly cannot model the business without understanding how customers use the product. Revenue, product usage, operational data, and financial results were always connected, and AI makes the connection impossible to ignore, because the gap between a customer paying and a customer consuming now carries a direct cost consequence.

The companies that understand AI economics best will not be those spending least on AI. They will be the ones that can trace how AI consumption becomes customer value, gross margin, and financial performance, and adjust product, pricing, and plan accordingly. That requires the same discipline separating deterministic calculation from AI interpretation, which we have written about in [why AI versus automation is the wrong question for Finance](/blog/ai-vs-automation-finance).

At SMPL.ai we build on that separation. The platform applies deterministic Finance logic to produce core calculations and SaaS metrics, and uses AI on top of that foundation to explain and contextualize results rather than to produce the numbers. The wider thinking behind that approach is set out in [the AI operating system for SaaS Finance](/blog/ai-operating-system-for-saas-finance).

The financial model has to reflect how the product actually works. AI has raised the cost of pretending otherwise.

## Frequently asked questions

**Are AI costs considered cost of goods sold (COGS) for SaaS companies?**

It depends on the nature of the cost and how the service is delivered. Inference and infrastructure costs directly associated with delivering a customer-facing service are commonly evaluated within cost of revenue, while model training, research, and internal tooling frequently sit elsewhere. Classification depends on your accounting policy and applicable guidance, so confirm treatment with your accounting team rather than applying a general rule. Where you draw the line materially changes reported gross margin.

**How does AI affect SaaS gross margin?**

AI introduces a delivery cost that scales with customer activity rather than sitting largely fixed. ICONIQ's State of AI 2026 report, published July 2026, puts AI product gross margins at 45 percent in 2025 with projections of 53 percent in 2026 and 59 percent in 2027. Bessemer Venture Partners' February 2026 pricing playbook describes AI companies at 50 to 60 percent gross margin against 80 to 90 percent for traditional SaaS. The impact on any individual company depends on how central AI is to the product and how it is engineered and priced.

**How should FP&A forecast AI COGS?**

Use a driver-based model rather than a percentage of revenue. A workable chain runs from customers, to active AI users per customer, to workflows per user, to model calls per workflow, to tokens per call, to cost per token by model. A percentage-of-revenue assumption implicitly assumes cost tracks billings, but in an AI product cost tracks usage, and under flat pricing those two can diverge substantially without revenue moving.

**Why is inference a growing share of AI product cost if token prices are falling?**

Two different measurements are involved. Andreessen Horowitz's 2024 "LLMflation" analysis found inference cost falling roughly 10x per year for a model of equivalent performance. ICONIQ's 2026 data shows model inference rising from 20 percent of AI product cost before launch to 23 percent at general availability and scale, while talent falls from 32 percent to 26 percent. The phrase "equivalent performance" reconciles them, because teams spend the price decline on added capability, so unit prices fall while units consumed rise and the cost base rotates from fixed toward variable.

**What metrics should Finance track for AI products?**

Begin with whichever operating metric best explains the change in AI cost of delivery. Common candidates include AI requests per customer, tokens per request, model mix, inference cost per workflow, AI cost per customer, AI cost as a share of ARR, and gross margin by customer or cohort. Materiality should govern the effort, since a company where AI infrastructure is a fraction of a percent of revenue does not need the instrumentation of one approaching double digits.

**How should SaaS companies price AI features?**

There is no universal answer, and the market is blending approaches. ICONIQ's July 2026 data shows consumption-based pricing rising from 35 to 42 percent of companies in six months, outcome-based pricing from 18 to 23 percent, and companies using an average of 1.7 pricing models at once. GitHub Copilot illustrates the hybrid pattern, combining since 1 June 2026 an unchanged base subscription with a monthly allotment of GitHub AI Credits priced from token consumption, plus metered overage. The question for Finance is whether the structure connects price to cost to serve closely enough that heavy usage does not quietly erode margin.

**Can AI-enabled SaaS still achieve high gross margins?**

Yes, depending on product design, model selection, caching, routing, and pricing structure. ICONIQ's projected trajectory from 45 percent in 2025 to 59 percent in 2027, and the gap between high-growth companies at a projected 64 percent and the rest at 58 percent, both suggest margin responds to management rather than being fixed by category. The caution is that inference becomes a larger share of the cost base as products mature, so improvement comes from deliberate engineering and pricing decisions rather than from waiting for model prices to fall.
