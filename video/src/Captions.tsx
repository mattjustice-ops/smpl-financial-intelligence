import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { brand } from "./brand";

export type CaptionCue = {
  startFrame: number;
  endFrame: number;
  text: string;
  /** Optional word to underline with teal (karaoke-style, matches Cube ref) */
  emphasize?: string;
};

export const Captions: React.FC<{ cues: CaptionCue[] }> = ({ cues }) => {
  const frame = useCurrentFrame();
  const cue = cues.find((c) => frame >= c.startFrame && frame < c.endFrame);
  if (!cue) return null;

  const local = frame - cue.startFrame;
  const opacity = interpolate(local, [0, 6], [0, 1], {
    extrapolateRight: "clamp",
  });

  const { text, emphasize } = cue;
  let content: React.ReactNode = text;
  if (emphasize && text.includes(emphasize)) {
    const i = text.indexOf(emphasize);
    content = (
      <>
        {text.slice(0, i)}
        <span
          style={{
            borderBottom: `2px solid ${brand.teal}`,
            paddingBottom: 2,
          }}
        >
          {emphasize}
        </span>
        {text.slice(i + emphasize.length)}
      </>
    );
  }

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: 64,
        opacity,
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          maxWidth: 1100,
          background: "rgba(0, 0, 0, 0.72)",
          borderRadius: 10,
          padding: "14px 28px",
          color: brand.white,
          fontFamily: brand.font,
          fontSize: 32,
          fontWeight: 500,
          lineHeight: 1.35,
          textAlign: "center",
          letterSpacing: "-0.01em",
        }}
      >
        {content}
      </div>
    </AbsoluteFill>
  );
};
