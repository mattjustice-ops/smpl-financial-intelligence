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
 * Scene 1 v3.2 — Finance-desk opening only (≈15s).
 * Recognition before explanation. Real logos. Concept subtitles.
 */
const VO = [
  { start: 2.0, end: 4.0, file: "vo/v32/o01.mp3" },
  { start: 4.1, end: 8.3, file: "vo/v32/o02.mp3" },
  { start: 8.4, end: 11.8, file: "vo/v32/o03.mp3" },
  { start: 11.9, end: 16.0, file: "vo/v32/o04.mp3" },
] as const;

/** Concept subtitles — reinforce ideas, not VO verbatim */
const SUBS = [
  { start: 2.0, end: 4.2, text: "Every month-end" },
  { start: 4.3, end: 8.4, text: "Days of manual reporting" },
  { start: 8.5, end: 11.9, text: "Executive reporting" },
  { start: 12.0, end: 16.0, text: "Fragmented systems" },
] as const;

type AppCard = {
  id: string;
  logo: string;
  title: string;
  subtitle: string;
  enter: number;
  x: number;
  y: number;
  w: number;
  h: number;
  logoBg?: string;
  logoPad?: number;
};

const APPS: AppCard[] = [
  {
    id: "salesforce",
    logo: "logos/salesforce.png",
    title: "Pipeline Forecast",
    subtitle: "Closed Won · Bookings · Commit",
    enter: 0.3,
    x: 80,
    y: 120,
    w: 420,
    h: 260,
  },
  {
    id: "netsuite",
    logo: "logos/netsuite.png",
    title: "Revenue Detail",
    subtitle: "Journal Entries · Financial Statements",
    enter: 1.1,
    x: 540,
    y: 90,
    w: 400,
    h: 240,
    logoBg: "#FFFFFF",
    logoPad: 10,
  },
  {
    id: "excel",
    logo: "logos/excel.png",
    title: "ARR Forecast_v9.xlsx",
    subtitle: "Bookings · Cash Flow · Revenue Bridge",
    enter: 2.0,
    x: 980,
    y: 140,
    w: 420,
    h: 270,
  },
  {
    id: "powerpoint",
    logo: "logos/powerpoint.png",
    title: "Board Meeting — Q3",
    subtitle: "Executive Review · Draft",
    enter: 3.0,
    x: 200,
    y: 420,
    w: 400,
    h: 240,
  },
  {
    id: "slack",
    logo: "logos/slack.png",
    title: "#fpna",
    subtitle: "Can someone verify ARR?",
    enter: 4.0,
    x: 640,
    y: 400,
    w: 340,
    h: 160,
  },
  {
    id: "teams",
    logo: "logos/teams.png",
    title: "Teams · Finance",
    subtitle: "Need latest board deck",
    enter: 5.0,
    x: 1020,
    y: 450,
    w: 340,
    h: 150,
  },
  {
    id: "outlook",
    logo: "logos/outlook.png",
    title: "Inbox",
    subtitle: "CEO: Forecast questions",
    enter: 6.0,
    x: 80,
    y: 700,
    w: 360,
    h: 140,
  },
  {
    id: "hubspot",
    logo: "logos/hubspot.png",
    title: "Marketing Ops",
    subtitle: "Pipeline influence · Attribution",
    enter: 7.0,
    x: 480,
    y: 680,
    w: 360,
    h: 150,
    logoBg: "#FFFFFF",
    logoPad: 8,
  },
  {
    id: "workday",
    logo: "logos/workday.png",
    title: "Workforce",
    subtitle: "Headcount · Comp · Ramp",
    enter: 8.0,
    x: 880,
    y: 680,
    w: 340,
    h: 150,
    logoBg: "#FFFFFF",
    logoPad: 8,
  },
  {
    id: "snowflake",
    logo: "logos/snowflake.png",
    title: "Warehouse",
    subtitle: "Finance mart · Exports",
    enter: 9.0,
    x: 1260,
    y: 300,
    w: 320,
    h: 160,
    logoBg: "#F5F7FA",
    logoPad: 10,
  },
];

const AppWindow: React.FC<{ app: AppCard }> = ({ app }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const start = Math.round(app.enter * fps);
  if (frame < start) return null;

  const t = interpolate(frame, [start, start + 18], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: ease,
  });
  const y = interpolate(frame, [start, start + 20], [16, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: ease,
  });

  return (
    <div
      style={{
        position: "absolute",
        left: app.x,
        top: app.y + y,
        width: app.w,
        height: app.h,
        opacity: t,
        borderRadius: 12,
        overflow: "hidden",
        background: "#0d1220",
        border: "1px solid rgba(255,255,255,0.12)",
        boxShadow: "0 24px 60px rgba(0,0,0,0.5)",
        fontFamily: brand.font,
      }}
    >
      <div
        style={{
          height: 40,
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "0 12px",
          background: "#161b2c",
          borderBottom: "1px solid rgba(255,255,255,0.06)",
        }}
      >
        <div style={{ display: "flex", gap: 5 }}>
          {["#ff5f57", "#febc2e", "#28c840"].map((c) => (
            <div key={c} style={{ width: 8, height: 8, borderRadius: "50%", background: c, opacity: 0.9 }} />
          ))}
        </div>
        <div
          style={{
            height: 22,
            borderRadius: 5,
            background: app.logoBg ?? "transparent",
            padding: app.logoPad ? `0 ${app.logoPad}px` : 0,
            display: "flex",
            alignItems: "center",
          }}
        >
          <Img
            src={staticFile(app.logo)}
            style={{ height: 18, width: "auto", objectFit: "contain", display: "block" }}
          />
        </div>
      </div>
      <div style={{ padding: "14px 16px" }}>
        <div style={{ color: brand.white, fontSize: 18, fontWeight: 600, letterSpacing: "-0.01em" }}>
          {app.title}
        </div>
        <div style={{ color: brand.muted, fontSize: 14, marginTop: 6 }}>{app.subtitle}</div>
        {/* Believable content stub */}
        <div style={{ marginTop: 14, display: "flex", gap: 8 }}>
          {[0.55, 0.8, 0.4].map((w, i) => (
            <div
              key={i}
              style={{
                flex: w,
                height: 8,
                borderRadius: 3,
                background: i === 1 ? brand.tealDim : "rgba(255,255,255,0.08)",
              }}
            />
          ))}
        </div>
        <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
          {[0.7, 0.5, 0.9].map((w, i) => (
            <div
              key={i}
              style={{
                flex: w,
                height: 8,
                borderRadius: 3,
                background: "rgba(255,255,255,0.06)",
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

const ConceptSub: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const cue = SUBS.find(
    (s) => frame >= Math.round(s.start * fps) && frame < Math.round(s.end * fps),
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
        paddingBottom: 56,
        opacity,
        pointerEvents: "none",
        zIndex: 40,
      }}
    >
      <div
        style={{
          background: "rgba(0,0,0,0.7)",
          borderRadius: 8,
          padding: "12px 22px",
          color: brand.white,
          fontFamily: brand.font,
          fontSize: 28,
          fontWeight: 500,
          letterSpacing: "-0.01em",
          borderBottom: `2px solid ${brand.teal}`,
        }}
      >
        {cue.text}
      </div>
    </AbsoluteFill>
  );
};

export const SCENE1_DURATION_FRAMES = 16 * 30;

export const Scene1: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Extremely subtle camera drift as desktop fills
  const drift = interpolate(frame, [0, 16 * fps], [0, -10], {
    extrapolateRight: "clamp",
    easing: ease,
  });
  const scale = interpolate(frame, [0, 16 * fps], [1.02, 1], {
    extrapolateRight: "clamp",
    easing: ease,
  });

  return (
    <AbsoluteFill style={{ backgroundColor: brand.bg, fontFamily: brand.font }}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 40% 35%, #0a1526 0%, ${brand.bg} 60%)`,
        }}
      />

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

      <div
        style={{
          width: "100%",
          height: "100%",
          transform: `translateY(${drift}px) scale(${scale})`,
          transformOrigin: "center center",
        }}
      >
        {APPS.map((app) => (
          <AppWindow key={app.id} app={app} />
        ))}
      </div>

      <ConceptSub />
    </AbsoluteFill>
  );
};
