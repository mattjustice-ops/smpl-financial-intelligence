import React from "react";
import {
  AbsoluteFill,
  Audio,
  Easing,
  interpolate,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { brand } from "./brand";
import { Captions, CaptionCue } from "./Captions";

/**
 * Shot 1 v2 — Cold open (0:00–0:11)
 * Concept: same ARR appears across moments with no source trail —
 * sets up the trust problem. Five-spoke device is reserved for Shot 4.
 */
/** Back-to-back Jenny clips (+30% rate) — sum ≈ 11.18s, fits the 11s budget */
const LINE_WINDOWS = [
  {
    start: 0,
    end: 2.568,
    file: "vo/01.mp3",
    text: "$18.7M ARR.",
    emphasize: "ARR",
  },
  {
    start: 2.568,
    end: 4.152,
    file: "vo/02.mp3",
    text: "Look at it right now.",
    emphasize: "now",
  },
  {
    start: 4.152,
    end: 6.0,
    file: "vo/03.mp3",
    text: "Look again this afternoon.",
    emphasize: "afternoon",
  },
  {
    start: 6.0,
    end: 8.184,
    file: "vo/04.mp3",
    text: "Look at last quarter's board deck.",
    emphasize: "board",
  },
  {
    start: 8.184,
    end: 11.184,
    file: "vo/05.mp3",
    text: "Same number. No way to tell why.",
    emphasize: "why",
  },
] as const;

type Instance = {
  /** when this instance becomes the focus */
  enter: number;
  /** when it settles / begins to fade back */
  exit: number;
  x: number;
  y: number;
  cue: string;
  scale: number;
};

/** 2–3 recurring instances of the same number, visually disconnected */
const INSTANCES: Instance[] = [
  { enter: 0, exit: 3.8, x: 960, y: 460, cue: "Right now", scale: 1 },
  { enter: 3.6, exit: 7.6, x: 580, y: 360, cue: "This afternoon", scale: 0.82 },
  {
    enter: 5.8,
    exit: 11,
    x: 1280,
    y: 620,
    cue: "Board Deck — Last Quarter",
    scale: 0.72,
  },
];

const softSpring = {
  damping: 200,
  stiffness: 80,
  mass: 0.8,
};

const NumberInstance: React.FC<{
  instance: Instance;
  index: number;
  alone: boolean;
}> = ({ instance, index, alone }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const enterF = Math.round(instance.enter * fps);
  const exitF = Math.round(instance.exit * fps);

  const appear = spring({
    frame: frame - enterF,
    fps,
    config: softSpring,
  });

  // Fade earlier instances down once later ones arrive (except final alone hold)
  const isLast = index === INSTANCES.length - 1;
  const dimStart = isLast ? exitF + 9999 : exitF;
  const dim = interpolate(frame, [dimStart, dimStart + Math.round(0.5 * fps)], [1, alone && isLast ? 1 : 0.22], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });

  // Final beat: only the primary number remains, centered-feeling, no cue
  const aloneMix = alone
    ? interpolate(frame, [8 * fps, 8.6 * fps], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: Easing.inOut(Easing.cubic),
      })
    : 0;

  if (frame < enterF) return null;

  const opacity = Math.min(1, appear) * dim * (alone && !isLast ? interpolate(aloneMix, [0, 1], [1, 0]) : 1);
  if (opacity < 0.01) return null;

  // Drift last instance toward center when alone
  const x = alone && isLast
    ? interpolate(aloneMix, [0, 1], [instance.x, 960])
    : instance.x;
  const y = alone && isLast
    ? interpolate(aloneMix, [0, 1], [instance.y, 460])
    : instance.y;
  const scale =
    (alone && isLast
      ? interpolate(aloneMix, [0, 1], [instance.scale, 1])
      : instance.scale) * (0.92 + 0.08 * Math.min(1, appear));

  const cueOpacity = alone && isLast
    ? interpolate(aloneMix, [0, 0.6], [1, 0], {
        extrapolateRight: "clamp",
      })
    : interpolate(frame, [enterF + 6, enterF + 16], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });

  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        transform: `translate(-50%, -50%) scale(${scale})`,
        opacity,
        textAlign: "center",
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          color: brand.white,
          fontSize: 96,
          fontWeight: 700,
          letterSpacing: "-0.04em",
          lineHeight: 1,
        }}
      >
        $18.7M
      </div>
      <div
        style={{
          marginTop: 10,
          color: brand.teal,
          fontSize: 22,
          fontWeight: 600,
          letterSpacing: "0.14em",
          textTransform: "uppercase",
        }}
      >
        ARR
      </div>
      <div
        style={{
          marginTop: 16,
          color: brand.muted,
          fontSize: 22,
          fontWeight: 500,
          letterSpacing: "0.02em",
          opacity: cueOpacity,
        }}
      >
        {instance.cue}
      </div>
      {/* No connector / trail — intentional absence */}
    </div>
  );
};

export const SHOT1_DURATION_FRAMES = Math.ceil(11.184 * 30); // ≈336 @ 30fps

export const Shot1: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const cues: CaptionCue[] = LINE_WINDOWS.map((w) => ({
    startFrame: Math.round(w.start * fps),
    endFrame: Math.round(w.end * fps),
    text: w.text,
    emphasize: w.emphasize,
  }));

  const alone = frame >= 8 * fps;

  // Soft glow — static, no oscillating pulse (avoids shakiness)
  const glowOpacity = interpolate(frame, [0, 12], [0, 1], {
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });

  return (
    <AbsoluteFill style={{ backgroundColor: brand.bg, fontFamily: brand.font }}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 50% 45%, ${brand.tealGlow} 0%, transparent 55%)`,
          opacity: glowOpacity,
        }}
      />

      {LINE_WINDOWS.map((w) => (
        <Sequence
          key={w.file}
          from={Math.round(w.start * fps)}
          durationInFrames={Math.max(1, Math.round((w.end - w.start) * fps))}
          layout="none"
        >
          <Audio src={staticFile(w.file)} />
        </Sequence>
      ))}

      {/* Staggered recurrence of the same number — no source edges */}
      {INSTANCES.map((inst, i) => (
        <NumberInstance
          key={inst.cue}
          instance={inst}
          index={i}
          alone={alone}
        />
      ))}

      {/* Final line overlay under the solitary number */}
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          paddingTop: 280,
          opacity: interpolate(frame, [8.8 * fps, 9.4 * fps], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.inOut(Easing.cubic),
          }),
          pointerEvents: "none",
        }}
      >
        <div
          style={{
            color: brand.muted,
            fontSize: 28,
            fontWeight: 500,
            letterSpacing: "0.01em",
          }}
        >
          No trail. No source. No why.
        </div>
      </AbsoluteFill>

      <Captions cues={cues} />
    </AbsoluteFill>
  );
};
