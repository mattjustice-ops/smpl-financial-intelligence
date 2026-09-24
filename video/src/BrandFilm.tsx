import React from "react";
import {
  AbsoluteFill,
  Audio,
  Easing,
  Img,
  interpolate,
  Sequence,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { brand } from "./brand";

const ease = Easing.inOut(Easing.cubic);

/**
 * SMPL Brand Film ~78s
 * Act 1 (hybrid): Month-End desk chaos → Slopes-style one ARR / four answers
 * Act 2: SMPL Operating Intelligence — trust, ARR explainability, board-ready
 */

const VO = [
  { start: 0.6, end: 5.5, file: "vo/hybrid/h01.mp3" },
  { start: 5.5, end: 9.1, file: "vo/hybrid/h02.mp3" },
  { start: 10.6, end: 13.2, file: "vo/hybrid/h03.mp3" },
  { start: 13.2, end: 18.9, file: "vo/hybrid/h04.mp3" },
  { start: 18.9, end: 21.6, file: "vo/hybrid/h05.mp3" },
  { start: 21.7, end: 24.3, file: "vo/hybrid/h06.mp3" },
  // freeze 24.3–26
  { start: 26.0, end: 29.5, file: "vo/full/s01.mp3" },
  { start: 29.5, end: 33.2, file: "vo/full/s02.mp3" },
  { start: 33.2, end: 38.2, file: "vo/full/s03.mp3" },
  { start: 38.3, end: 45.4, file: "vo/full/s05.mp3" },
  { start: 45.4, end: 54.3, file: "vo/full/s06.mp3" },
  { start: 54.4, end: 62.4, file: "vo/full/s07.mp3" },
  { start: 62.5, end: 68.9, file: "vo/full/s08.mp3" },
  { start: 69.0, end: 73.2, file: "vo/full/s09.mp3" },
] as const;

const SUBS = [
  { start: 0.6, end: 5.5, text: "Month-end reality" },
  { start: 5.5, end: 9.5, text: "Systems that never agree" },
  { start: 9.5, end: 10.8, text: "One month-end. Six places." },
  { start: 10.6, end: 13.2, text: "It starts with one number" },
  { start: 13.2, end: 18.9, text: "CRM → ERP → Excel → Deck" },
  { start: 18.9, end: 21.6, text: "Four different answers" },
  { start: 21.7, end: 24.5, text: "This is modern finance" },
  { start: 26.0, end: 33.2, text: "One operating system" },
  { start: 33.2, end: 38.2, text: "One finance model" },
  { start: 38.3, end: 45.4, text: "ARR that explains itself" },
  { start: 45.4, end: 54.3, text: "Evidence, not vibes" },
  { start: 54.4, end: 62.4, text: "Traceable answers" },
  { start: 62.5, end: 68.9, text: "Board-ready" },
  { start: 69.0, end: 78.0, text: "Built to be trusted" },
] as const;

const LOGOS = [
  { id: "salesforce", file: "logos/salesforce.png", enter: 0.3, x: 70, y: 70, w: 380, title: "Pipeline · Closed Won", bg: undefined as string | undefined },
  { id: "netsuite", file: "logos/netsuite.png", enter: 0.9, x: 520, y: 50, w: 360, title: "Revenue Detail", bg: "#fff" },
  { id: "excel", file: "logos/excel.png", enter: 1.5, x: 960, y: 90, w: 420, title: "Executive_Reporting_v18.xlsx", bg: undefined },
  { id: "powerpoint", file: "logos/powerpoint.png", enter: 2.4, x: 140, y: 360, w: 400, title: "Executive Business Review", bg: undefined },
  { id: "slack", file: "logos/slack.png", enter: 3.2, x: 620, y: 390, w: 360, title: "#fpna · verify ARR?", bg: undefined },
  { id: "outlook", file: "logos/outlook.png", enter: 4.0, x: 1080, y: 420, w: 340, title: "Board Deck Comments", bg: undefined },
  { id: "teams", file: "logos/teams.png", enter: 4.8, x: 90, y: 680, w: 320, title: "Forecast update?", bg: undefined },
  { id: "hubspot", file: "logos/hubspot.png", enter: 5.4, x: 480, y: 680, w: 320, title: "Pipeline influence", bg: "#fff" },
  { id: "workday", file: "logos/workday.png", enter: 6.0, x: 880, y: 660, w: 300, title: "Headcount · Comp", bg: "#fff" },
  { id: "snowflake", file: "logos/snowflake.png", enter: 6.6, x: 1280, y: 220, w: 300, title: "Finance mart export", bg: "#F5F7FA" },
] as const;

function fade(frame: number, start: number, dur = 16) {
  return interpolate(frame, [start, start + dur], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: ease,
  });
}

const ConceptSub: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const cue = SUBS.find(
    (s) => frame >= s.start * fps && frame < s.end * fps,
  );
  if (!cue) return null;
  const local = frame - Math.round(cue.start * fps);
  const opacity = interpolate(local, [0, 8], [0, 1], {
    extrapolateRight: "clamp",
    easing: ease,
  });
  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: 48,
        opacity,
        zIndex: 50,
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          background: "rgba(0,0,0,0.72)",
          borderRadius: 8,
          padding: "11px 20px",
          color: brand.white,
          fontFamily: brand.font,
          fontSize: 26,
          fontWeight: 500,
          borderBottom: `2px solid ${brand.teal}`,
        }}
      >
        {cue.text}
      </div>
    </AbsoluteFill>
  );
};

/** Act 1 — hybrid: lived-in month-end desk → one ARR fans into four answers */
const ProblemAct: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (frame > 26 * fps) return null;

  const deskEnd = 10.4 * fps;
  const slopesStart = 10.2 * fps;
  const freezeStart = 24.3 * fps;

  const deskOpacity = interpolate(
    frame,
    [deskEnd - 8, deskEnd + 6],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease },
  );
  const slopesOpacity = interpolate(
    frame,
    [slopesStart, slopesStart + 12, freezeStart, freezeStart + 20],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease },
  );

  const punchline = fade(frame, 9.0 * fps, 12);
  const punchlineOut = interpolate(frame, [10.0 * fps, 10.6 * fps], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Slopes divergence
  const hub = { x: 280, y: 470 };
  const spokes = [
    { file: "logos/salesforce.png", angle: -42, out: "$19.1M", color: "#00A1E0", label: "CRM" },
    { file: "logos/netsuite.png", angle: -8, out: "$18.4M", color: "#C74634", label: "ERP", bg: "#fff" },
    { file: "logos/excel.png", angle: 28, out: "$18.7M", color: "#217346", label: "Excel" },
    { file: "logos/powerpoint.png", angle: 62, out: "$18.9M", color: "#C43E1C", label: "Deck" },
  ];
  const lineDraw = interpolate(frame, [13.5 * fps, 16.5 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: ease,
  });
  const outsIn = fade(frame, 18.5 * fps, 14);
  const modernFinance = fade(frame, 21.7 * fps, 14);

  return (
    <AbsoluteFill>
      {/* —— Month-End Reality desk —— */}
      <AbsoluteFill style={{ opacity: deskOpacity }}>
        <AbsoluteFill
          style={{
            background: `radial-gradient(ellipse at 45% 30%, #0c1830 0%, #02040c 70%)`,
          }}
        />
        {/* faux ambient “late night” taskbar */}
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            bottom: 0,
            height: 42,
            background: "rgba(8,12,22,0.92)",
            borderTop: "1px solid rgba(255,255,255,0.08)",
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "0 18px",
            opacity: fade(frame, 0.2 * fps, 20),
          }}
        >
          {LOGOS.slice(0, 8).map((l) => (
            <div
              key={l.id}
              style={{
                background: l.bg ?? "transparent",
                borderRadius: 4,
                padding: l.bg ? 3 : 0,
                height: 22,
                display: "flex",
                alignItems: "center",
              }}
            >
              <Img src={staticFile(l.file)} style={{ height: 16, width: "auto" }} />
            </div>
          ))}
          <div style={{ marginLeft: "auto", color: brand.muted, fontSize: 13, fontFamily: brand.font }}>
            12:33 AM
          </div>
        </div>

        {LOGOS.map((l, i) => {
          const start = Math.round(l.enter * fps);
          if (frame < start) return null;
          const o = fade(frame, start);
          const y = interpolate(frame, [start, start + 16], [18, 0], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: ease,
          });
          const rot = ((i % 3) - 1) * 1.2;
          return (
            <div
              key={l.id}
              style={{
                position: "absolute",
                left: l.x,
                top: l.y + y,
                width: l.w,
                opacity: o,
                transform: `rotate(${rot}deg)`,
                borderRadius: 10,
                background: "#0d1220",
                border: "1px solid rgba(255,255,255,0.14)",
                boxShadow: "0 28px 70px rgba(0,0,0,0.55)",
                overflow: "hidden",
                fontFamily: brand.font,
              }}
            >
              <div
                style={{
                  height: 34,
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "0 10px",
                  background: "#151b2c",
                }}
              >
                <div style={{ display: "flex", gap: 5 }}>
                  {["#ff5f57", "#febc2e", "#28c840"].map((c) => (
                    <div key={c} style={{ width: 7, height: 7, borderRadius: "50%", background: c }} />
                  ))}
                </div>
                <div
                  style={{
                    background: l.bg ?? "transparent",
                    borderRadius: 4,
                    padding: l.bg ? "2px 5px" : 0,
                    height: 20,
                    display: "flex",
                    alignItems: "center",
                  }}
                >
                  <Img src={staticFile(l.file)} style={{ height: 14, width: "auto" }} />
                </div>
                <div style={{ color: brand.muted, fontSize: 12, overflow: "hidden", whiteSpace: "nowrap" }}>
                  {l.title}
                </div>
              </div>
              <div style={{ padding: 12 }}>
                {l.id === "excel" ? (
                  <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr 1fr 1fr", gap: 3 }}>
                    {["", "Q1", "Q2", "Q3", "ARR", "18.1", "18.4", "18.7", "Bookings", "4.2", "3.9", "4.6"].map(
                      (cell, ci) => (
                        <div
                          key={ci}
                          style={{
                            background: ci > 0 && ci < 4 ? "#1a2336" : "rgba(255,255,255,0.05)",
                            color: brand.muted,
                            fontSize: 11,
                            padding: "5px 6px",
                          }}
                        >
                          {cell}
                        </div>
                      ),
                    )}
                  </div>
                ) : (
                  <>
                    <div style={{ height: 8, width: "75%", background: "rgba(255,255,255,0.1)", borderRadius: 3 }} />
                    <div style={{ height: 8, width: "50%", marginTop: 8, background: "rgba(255,255,255,0.06)", borderRadius: 3 }} />
                    <div style={{ height: 8, width: "62%", marginTop: 8, background: brand.tealDim, borderRadius: 3 }} />
                  </>
                )}
              </div>
            </div>
          );
        })}

        {/* Slack-ish toast */}
        <div
          style={{
            position: "absolute",
            right: 48,
            top: 160,
            width: 300,
            opacity: fade(frame, 3.4 * fps, 14),
            background: "#1a1d21",
            borderRadius: 12,
            border: "1px solid rgba(255,255,255,0.1)",
            padding: 14,
            fontFamily: brand.font,
            zIndex: 5,
          }}
        >
          <div style={{ color: brand.muted, fontSize: 12, marginBottom: 6 }}>Slack · #fpna</div>
          <div style={{ color: brand.white, fontSize: 15 }}>Can someone verify ARR?</div>
        </div>

        <div
          style={{
            position: "absolute",
            left: 80,
            bottom: 90,
            opacity: punchline * punchlineOut,
            color: brand.white,
            fontFamily: brand.font,
            fontSize: 40,
            fontWeight: 600,
            letterSpacing: "-0.02em",
            textShadow: "0 8px 30px rgba(0,0,0,0.8)",
            maxWidth: 900,
            zIndex: 6,
          }}
        >
          One month-end. Six places to find the answer.
        </div>
      </AbsoluteFill>

      {/* —— Slopes-style divergence —— */}
      <AbsoluteFill style={{ opacity: slopesOpacity, backgroundColor: brand.bg }}>
        <AbsoluteFill
          style={{
            background: `radial-gradient(circle at 28% 48%, ${brand.tealGlow} 0%, transparent 45%)`,
          }}
        />

        {/* Origin number */}
        <div
          style={{
            position: "absolute",
            left: 120,
            top: 400,
            opacity: fade(frame, 10.5 * fps, 14),
            fontFamily: brand.font,
          }}
        >
          <div
            style={{
              width: 18,
              height: 18,
              borderRadius: "50%",
              background: brand.teal,
              boxShadow: `0 0 0 8px ${brand.tealGlow}`,
              marginBottom: 18,
            }}
          />
          <div style={{ color: brand.white, fontSize: 72, fontWeight: 700, letterSpacing: "-0.04em" }}>
            $18.7M
          </div>
          <div style={{ color: brand.teal, fontSize: 22, fontWeight: 600, letterSpacing: "0.14em", marginTop: 6 }}>
            ARR
          </div>
        </div>

        <svg
          width={1920}
          height={1080}
          style={{ position: "absolute", inset: 0, pointerEvents: "none" }}
        >
          {spokes.map((s) => {
            const rad = (s.angle * Math.PI) / 180;
            const ex = hub.x + Math.cos(rad) * 520 * lineDraw;
            const ey = hub.y + Math.sin(rad) * 280 * lineDraw;
            return (
              <line
                key={s.file}
                x1={hub.x}
                y1={hub.y}
                x2={ex}
                y2={ey}
                stroke={s.color}
                strokeWidth={2.5}
                strokeLinecap="round"
                opacity={0.85}
              />
            );
          })}
        </svg>

        {spokes.map((s) => {
          const rad = (s.angle * Math.PI) / 180;
          const ex = hub.x + Math.cos(rad) * 520;
          const ey = hub.y + Math.sin(rad) * 280;
          const nodeO = fade(frame, 14.2 * fps, 14);
          return (
            <div key={s.file} style={{ position: "absolute", left: ex, top: ey, transform: "translate(-50%, -50%)", opacity: nodeO * lineDraw }}>
              <div
                style={{
                  width: 64,
                  height: 64,
                  borderRadius: "50%",
                  background: s.bg ?? "#0d1220",
                  border: `2px solid ${s.color}`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: `0 0 24px ${s.color}44`,
                }}
              >
                <Img src={staticFile(s.file)} style={{ height: 22, width: "auto" }} />
              </div>
              <div
                style={{
                  marginTop: 10,
                  textAlign: "center",
                  opacity: outsIn,
                  fontFamily: brand.font,
                }}
              >
                <div style={{ color: s.color, fontSize: 28, fontWeight: 700 }}>{s.out}</div>
                <div style={{ color: brand.muted, fontSize: 13 }}>{s.label}</div>
              </div>
            </div>
          );
        })}

        {/* Modern finance title card */}
        <AbsoluteFill
          style={{
            justifyContent: "center",
            alignItems: "center",
            opacity: modernFinance,
            backgroundColor: frame >= 21.7 * fps ? brand.bg : "transparent",
          }}
        >
          {frame >= 21.7 * fps && (
            <div
              style={{
                color: brand.white,
                fontFamily: brand.font,
                fontSize: 56,
                fontWeight: 500,
                letterSpacing: "-0.03em",
              }}
            >
              This is modern finance.
            </div>
          )}
        </AbsoluteFill>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/** Act 2a — SMPL reveal + systems converge into Ending ARR */
const RevealAct: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (frame < 24 * fps || frame > 40 * fps) return null;

  const logoIn = fade(frame, 25.5 * fps, 20);
  const converge = interpolate(frame, [33 * fps, 37.5 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: ease,
  });
  const numberIn = fade(frame, 36 * fps, 18);

  const ring = [
    { file: "logos/salesforce.png", a: -140 },
    { file: "logos/netsuite.png", a: -90, bg: "#fff" },
    { file: "logos/excel.png", a: -40 },
    { file: "logos/powerpoint.png", a: 10 },
    { file: "logos/slack.png", a: 60 },
    { file: "logos/workday.png", a: 110, bg: "#fff" },
    { file: "logos/snowflake.png", a: 155, bg: "#F5F7FA" },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: brand.bg }}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(circle at 50% 45%, ${brand.tealGlow} 0%, transparent 50%)`,
          opacity: logoIn,
        }}
      />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", opacity: logoIn }}>
        <Img src={staticFile("smpl-lockup.png")} style={{ width: 520, height: "auto" }} />
        <div
          style={{
            position: "absolute",
            top: "62%",
            color: brand.muted,
            fontSize: 22,
            fontFamily: brand.font,
            letterSpacing: "0.04em",
          }}
        >
          Operating Intelligence
        </div>
      </AbsoluteFill>

      {/* Converge logos into center number */}
      <AbsoluteFill style={{ opacity: converge }}>
        {ring.map((r) => {
          const rad = (r.a * Math.PI) / 180;
          const dist = interpolate(converge, [0, 1], [340, 0]);
          const cx = 960 + Math.cos(rad) * dist;
          const cy = 480 + Math.sin(rad) * dist;
          return (
            <div
              key={r.file}
              style={{
                position: "absolute",
                left: cx,
                top: cy,
                transform: "translate(-50%, -50%)",
                background: r.bg ?? "rgba(255,255,255,0.06)",
                borderRadius: 10,
                padding: 8,
                opacity: interpolate(converge, [0, 0.85, 1], [1, 1, 0]),
              }}
            >
              <Img src={staticFile(r.file)} style={{ height: 28, width: "auto" }} />
            </div>
          );
        })}
        <div
          style={{
            position: "absolute",
            left: "50%",
            top: "48%",
            transform: "translate(-50%, -50%)",
            opacity: numberIn,
            textAlign: "center",
            fontFamily: brand.font,
          }}
        >
          <div style={{ color: brand.white, fontSize: 96, fontWeight: 700, letterSpacing: "-0.04em" }}>
            $18.7M
          </div>
          <div
            style={{
              color: brand.teal,
              fontSize: 24,
              fontWeight: 600,
              letterSpacing: "0.16em",
              marginTop: 8,
            }}
          >
            ENDING ARR
          </div>
          <div style={{ color: brand.muted, fontSize: 18, marginTop: 10 }}>
            Traceable to source · Same number every time
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/** Act 2b — ARR Waterfall + Expansion callout (real SMPL differentiator) */
const ArrExplainAct: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (frame < 38 * fps || frame > 55 * fps) return null;
  const o = fade(frame, 38.2 * fps, 16);
  const callout = fade(frame, 46 * fps, 16);

  const rows = [
    { l: "Beginning ARR", v: "$17.9M", dim: false },
    { l: "New", v: "+$0.6M", dim: false },
    { l: "Expansion", v: "+$0.8M", dim: false, accent: true },
    { l: "Contraction", v: "−$0.2M", dim: true },
    { l: "Churn", v: "−$0.4M", dim: true },
    { l: "Ending ARR", v: "$18.7M", dim: false, bold: true },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: brand.bg, opacity: o, fontFamily: brand.font }}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 30% 40%, ${brand.tealGlow} 0%, transparent 55%)`,
        }}
      />
      <div style={{ position: "absolute", left: 120, top: 140, width: 720 }}>
        <div style={{ color: brand.muted, fontSize: 14, letterSpacing: "0.12em", marginBottom: 8 }}>
          SMPL · ARR / MRR WATERFALL
        </div>
        <div style={{ color: brand.white, fontSize: 32, fontWeight: 600, marginBottom: 24 }}>
          Why ARR moved
        </div>
        {rows.map((r, i) => {
          const rowO = fade(frame, (39 + i * 0.45) * fps, 12);
          return (
            <div
              key={r.l}
              style={{
                display: "flex",
                justifyContent: "space-between",
                padding: "12px 0",
                borderBottom: "1px solid rgba(255,255,255,0.08)",
                opacity: rowO,
                color: r.accent ? brand.teal : r.dim ? brand.muted : brand.white,
                fontWeight: r.bold || r.accent ? 700 : 500,
                fontSize: r.bold ? 22 : 18,
              }}
            >
              <span>{r.l}</span>
              <span>{r.v}</span>
            </div>
          );
        })}
      </div>

      <div
        style={{
          position: "absolute",
          right: 100,
          top: 220,
          width: 560,
          opacity: callout,
          background: "#0d1528",
          border: `1px solid ${brand.tealDim}`,
          borderRadius: 14,
          padding: 28,
          boxShadow: `0 0 40px ${brand.tealGlow}`,
        }}
      >
        <div style={{ color: brand.teal, fontSize: 13, fontWeight: 700, letterSpacing: "0.1em", marginBottom: 12 }}>
          SMPL COPILOT · PRIMARY DRIVER
        </div>
        <div style={{ color: brand.white, fontSize: 22, fontWeight: 600, lineHeight: 1.45 }}>
          Expansion ARR was favorable to forecast by $420K — three enterprise upsells closed early.
        </div>
        <div style={{ marginTop: 18, color: brand.muted, fontSize: 14, lineHeight: 1.5 }}>
          Linked: Opportunity · Contract · Journal
        </div>
        <div
          style={{
            marginTop: 20,
            padding: "10px 12px",
            borderRadius: 8,
            background: "rgba(255,255,255,0.04)",
            color: "rgba(255,255,255,0.35)",
            textDecoration: "line-through",
            fontSize: 14,
          }}
        >
          “Revenue increased due to strong performance.”
        </div>
      </div>
    </AbsoluteFill>
  );
};

/** Act 2c — Board Platform trust strip */
const BoardAct: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (frame < 54 * fps || frame > 69 * fps) return null;
  const o = fade(frame, 54.5 * fps, 16);

  const kpis = [
    { l: "Ending ARR", v: "$18.7M" },
    { l: "Revenue (CM)", v: "$1.52M" },
    { l: "Ending Cash", v: "$42.1M" },
    { l: "Data Trust", v: "Clear", good: true },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: brand.bg, opacity: o, fontFamily: brand.font }}>
      <div style={{ position: "absolute", left: 140, top: 160, right: 140 }}>
        <div style={{ color: brand.muted, fontSize: 14, letterSpacing: "0.12em" }}>SMPL · BOARD PLATFORM</div>
        <div style={{ color: brand.white, fontSize: 36, fontWeight: 600, marginTop: 8, marginBottom: 28 }}>
          Board-ready. Validated. Traceable.
        </div>
        <div style={{ display: "flex", gap: 14, marginBottom: 28 }}>
          {kpis.map((k) => (
            <div
              key={k.l}
              style={{
                flex: 1,
                background: "#0d1528",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 12,
                padding: 18,
              }}
            >
              <div style={{ color: brand.muted, fontSize: 13 }}>{k.l}</div>
              <div
                style={{
                  color: k.good ? "#3DDC97" : brand.white,
                  fontSize: 28,
                  fontWeight: 700,
                  marginTop: 6,
                }}
              >
                {k.v}
              </div>
            </div>
          ))}
        </div>
        <div style={{ display: "flex", gap: 14 }}>
          {["Board presentation", "MD&A workbook", "ARR waterfall"].map((a) => (
            <div
              key={a}
              style={{
                flex: 1,
                padding: "16px 18px",
                borderRadius: 10,
                background: "rgba(48,207,202,0.08)",
                border: `1px solid ${brand.tealDim}`,
                color: brand.white,
                fontSize: 16,
                fontWeight: 500,
              }}
            >
              {a}
            </div>
          ))}
        </div>
        <div
          style={{
            marginTop: 22,
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            padding: "8px 14px",
            borderRadius: 999,
            background: "rgba(61,220,151,0.12)",
            color: "#3DDC97",
            fontSize: 14,
            fontWeight: 600,
          }}
        >
          ✓ Validation clear
        </div>
      </div>
    </AbsoluteFill>
  );
};

/** Act 2d — Close */
const CtaAct: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (frame < 68 * fps) return null;
  const o = fade(frame, 68.5 * fps, 18);
  const line2 = fade(frame, 70.5 * fps, 16);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: brand.bg,
        opacity: o,
        justifyContent: "center",
        alignItems: "center",
        fontFamily: brand.font,
      }}
    >
      <AbsoluteFill
        style={{
          background: `radial-gradient(circle at 50% 40%, ${brand.tealGlow} 0%, transparent 55%)`,
        }}
      />
      <Img src={staticFile("smpl-lockup.png")} style={{ width: 420, height: "auto", marginBottom: 28 }} />
      <div style={{ color: brand.white, fontSize: 40, fontWeight: 500, letterSpacing: "-0.02em", textAlign: "center" }}>
        Built to be trusted.
      </div>
      <div
        style={{
          marginTop: 16,
          color: brand.muted,
          fontSize: 20,
          opacity: line2,
          textAlign: "center",
          maxWidth: 640,
        }}
      >
        The AI operating system for SaaS finance teams.
      </div>
    </AbsoluteFill>
  );
};

export const BRAND_FILM_FRAMES = 78 * 30;

export const BrandFilm: React.FC = () => {
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill style={{ backgroundColor: brand.bg }}>
      {VO.map((w) => (
        <Sequence
          key={w.file}
          from={Math.round(w.start * fps)}
          durationInFrames={Math.max(1, Math.round((w.end - w.start) * fps))}
          layout="none"
        >
          <Audio src={staticFile(w.file)} />
        </Sequence>
      ))}

      <ProblemAct />
      <RevealAct />
      <ArrExplainAct />
      <BoardAct />
      <CtaAct />
      <ConceptSub />
    </AbsoluteFill>
  );
};
