# SMPL.ai — Video Script, Storyboard & Build Prompt

**Target length:** 75–90 seconds
**Reference model:** Cube's "AI Collaboration" video (structure and pacing), adapted to SMPL's real positioning per the Company Context document
**Skills required:** `explainer-video-skills` (explainer-video, diagram-animation), `kinetic-typography-skills` — see install commands at the bottom

---

## Part 1 — Full Script (timed, caption-style)

| Time | Line |
|---|---|
| 0:00–0:03 | "$42.1 million." |
| 0:03–0:07 | "Ask five people in your company what that number means." |
| 0:07–0:11 | "You'll get five different answers." |
| 0:11–0:15 | "One from the CRM. One from the ERP." |
| 0:15–0:19 | "One from last month's board deck." |
| 0:19–0:23 | "One somebody typed into a spreadsheet at 11pm before the meeting." |
| 0:23–0:27 | "That's not a data problem." |
| 0:27–0:30 | "That's a trust problem." |
| 0:30–0:33 | "This is SMPL." |
| 0:33–0:38 | "Every system your finance team touches — CRM, billing, payroll, the GL —" |
| 0:38–0:42 | "unified into one number." |
| 0:42–0:46 | "Not a copy of it. The actual, traceable thing." |
| 0:46–0:50 | "Every calculation traces back to the source." |
| 0:50–0:54 | "The same number, every time you ask." |
| 0:54–0:58 | "When ARR moves, SMPL doesn't just show you a chart." |
| 0:58–1:02 | "It tells you why." |
| 1:02–1:09 | "'Expansion ARR was favorable to forecast by $420K — three enterprise upsells closed early.'" |
| 1:09–1:13 | "Not 'revenue increased due to strong performance.'" |
| 1:13–1:15 | "The real reason." |
| 1:15–1:19 | "Nothing is ever silently rewritten." |
| 1:19–1:24 | "The board deck from March always matches what March actually said." |
| 1:24–1:28 | "Finance doesn't need another dashboard." |
| 1:28–1:32 | "It needs one number it can stand behind." |
| 1:32–1:36 | "SMPL. Built to be trusted." |

**Word count: ~210** — on target for a 75–90 second runtime at a natural narration pace.

---

## Part 2 — Shot-by-Shot Storyboard

Each shot names the skill from the installed packs that should build it. This is written so it can be handed directly to Claude Code once the skills are installed (see Part 3).

### Shot 1 — Cold open (0:00–0:11)
**Skill: `diagram-animation`**
Large number "$42.1M" alone on screen, center-left. Five thin lines animate outward from it, each terminating in a different icon/label: CRM, ERP, Board Deck, Spreadsheet, and one left deliberately blank/question-marked. Lines are different colors, echoing "five different answers." No logos needed yet — generic system icons are fine.

### Shot 2 — The problem stated (0:23–0:30)
**Skill: `kinetic-typography`**
Screen goes to solid dark background. "That's not a data problem." fades/types in, holds half a second, then "That's a trust problem." replaces it — "trust" emphasized (color shift or weight change). This is the pivot moment; keep it visually quiet so the line lands.

### Shot 3 — Brand reveal (0:30–0:33)
**Skill: `kinetic-typography` or `explainer-video` title card**
SMPL logo/wordmark animates in cleanly. Simple, confident, no clutter. (Needs actual brand assets — see Company Context §8.)

### Shot 4 — Unification (0:33–0:46)
**Skill: `diagram-animation`**
Mirror of Cube's central hub shot, but the framing should emphasize *traceability* over *unification alone* per the differentiator note — e.g., lines don't just converge into a central node, they visibly continue *through* it to a labeled "source record" layer underneath, reinforcing "not a copy of it, the actual traceable thing."

### Shot 5 — The explanation moment (0:54–1:13)
**Skill: `explainer-video` (primary narrative beat) + `diagram-animation` for the ARR line chart**
An ARR trend line ticks upward with a small favorable variance callout. As the VO delivers the specific example line, the exact text ("Expansion ARR was favorable to forecast by $420K...") appears as an actual on-screen annotation next to the chart — this is the single most important visual proof point in the video. Follow immediately with a brief, deliberately generic-looking counter-example ("Revenue increased due to strong performance") shown crossed out or grayed out, to land the contrast fast.

### Shot 6 — Immutability (1:15–1:24)
**Skill: `diagram-animation` or `explainer-video`**
Two versions of a board deck shown side by side or in sequence — labeled "March" and "Today" — with identical numbers, a small checkmark or timestamp confirming the match. Visually simple; the point is reassurance, not spectacle.

### Shot 7 — Closing statement (1:24–1:36)
**Skill: `kinetic-typography`**
"Finance doesn't need another dashboard." / "It needs one number it can stand behind." as sequential kinetic type, then the SMPL wordmark returns with the closing line "Built to be trusted."

---

## Part 3 — Setup and Kickoff Prompt

### Install (run once, in your project directory, with Node.js available)

```
npx skills add iart-ai/explainer-video-skills
npx skills add iart-ai/kinetic-typography-skills
```

### Kickoff prompt for Claude Code

Copy this in as your first message once the skills are installed. Attach the Company Context document and this document alongside it.

> I'm building a 75–90 second product explainer video for my company, SMPL.ai. I've attached our company context doc and a full script + shot-by-shot storyboard. Please build this as a sequence of scenes:
>
> - Shot 1 and Shot 4 should use the diagram-animation skill — progressive node/connector reveals, per the storyboard.
> - Shots 2, 3, and 7 should use kinetic typography for the text moments.
> - Shot 5 is the most important beat in the video — it needs a real ARR line chart with the specific variance callout text visible on screen exactly as written in the script, not paraphrased.
> - Match the narration timing in the script table as closely as possible; don't compress or pad individual lines.
> - Use a dark background with a single accent color (I'll provide our brand palette — ask me for it if it's not attached) rather than a busy multi-color palette.
> - Render a first draft of the full sequence so I can review pacing before we polish individual scenes.
>
> Start with Shot 1 as a standalone render so I can confirm the visual style before we build the rest.

---

## Notes for whoever directs this before it's finalized

- The script currently uses an **illustrative** example ($42.1M, the $420K variance line). If there's a real customer number or a real approved example that can be used instead, swap it in — real specifics will always land harder than illustrative ones.
- Brand colors/logo are not yet specified here — supply them before the first real render, not after, so Shot 3 and the closing card don't have to be redone.
- This script deliberately leads with trust/explainability rather than "unified data," per the differentiator note in the Company Context doc — worth confirming that's the angle leadership actually wants before locking the voiceover.
