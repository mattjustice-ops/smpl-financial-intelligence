"use client";

import { useEffect, useState } from "react";

const SKINS = [
  { id: "canvas", label: "Canvas" },
  { id: "smpl", label: "SMPL" },
  { id: "midnight", label: "Midnight" },
  { id: "harbor", label: "Harbor" },
  { id: "eclipse", label: "Eclipse" },
  { id: "graphite", label: "Graphite" },
  { id: "aurora", label: "Aurora" },
  { id: "ember", label: "Ember" },
  { id: "slate", label: "Slate" },
  { id: "mist", label: "Mist" },
] as const;

const SKIN_VARS: Record<string, Record<string, string>> = {
  canvas: {
    "--bg": "#18241b",
    "--bg2": "#23332699",
    "--card": "#233326",
    "--panel": "#2b3c2e",
    "--text": "#dde8d6",
    "--muted": "#72826a",
    "--border": "#2e3f31",
    "--border-subtle": "#2e3f31",
    "--accent": "#c4855a",
    "--positive": "#5fa878",
    "--negative": "#b8705f",
    "--watch": "#b89060",
  },
  smpl: {
    "--bg": "#0c1418",
    "--bg2": "#14222899",
    "--card": "#142228",
    "--panel": "#1a2e35",
    "--text": "#d8eae8",
    "--muted": "#5e8280",
    "--border": "#1e3540",
    "--border-subtle": "#1e3540",
    "--accent": "#3db8a6",
    "--positive": "#4aaa94",
    "--negative": "#b87068",
    "--watch": "#c4924a",
  },
  midnight: {
    "--bg": "#141a2e",
    "--bg2": "#1e273f99",
    "--card": "#1e273f",
    "--panel": "#252e4a",
    "--text": "#d8daf0",
    "--muted": "#606880",
    "--border": "#2c3558",
    "--border-subtle": "#2c3558",
    "--accent": "#c4a058",
    "--positive": "#5ea87a",
    "--negative": "#b87070",
    "--watch": "#c4a058",
  },
  harbor: {
    "--bg": "#0e2428",
    "--bg2": "#16363999",
    "--card": "#163639",
    "--panel": "#1d4045",
    "--text": "#d2e8e4",
    "--muted": "#567874",
    "--border": "#244850",
    "--border-subtle": "#244850",
    "--accent": "#c49058",
    "--positive": "#52a882",
    "--negative": "#b87068",
    "--watch": "#c49058",
  },
  eclipse: {
    "--bg": "#0d1018",
    "--bg2": "#181e2e",
    "--card": "#181e2e",
    "--panel": "#202638",
    "--text": "#d4d8e8",
    "--muted": "#586080",
    "--border": "#282f48",
    "--border-subtle": "#282f48",
    "--accent": "#6090c8",
    "--positive": "#52a882",
    "--negative": "#b07070",
    "--watch": "#b8904a",
  },
  graphite: {
    "--bg": "#141311",
    "--bg2": "#221f1c",
    "--card": "#221f1c",
    "--panel": "#2c2924",
    "--text": "#dedad4",
    "--muted": "#706860",
    "--border": "#363028",
    "--border-subtle": "#363028",
    "--accent": "#c0825a",
    "--positive": "#5aa87a",
    "--negative": "#b07060",
    "--watch": "#c0825a",
  },
  aurora: {
    "--bg": "#0c1020",
    "--bg2": "#161e30",
    "--card": "#161e30",
    "--panel": "#1e283e",
    "--text": "#ccd8ec",
    "--muted": "#506080",
    "--border": "#263450",
    "--border-subtle": "#263450",
    "--accent": "#5090c0",
    "--positive": "#4898a0",
    "--negative": "#a87070",
    "--watch": "#a89050",
  },
  ember: {
    "--bg": "#160f12",
    "--bg2": "#261a20",
    "--card": "#261a20",
    "--panel": "#302028",
    "--text": "#e8dcd8",
    "--muted": "#785850",
    "--border": "#3c2830",
    "--border-subtle": "#3c2830",
    "--accent": "#c09050",
    "--positive": "#5aa87a",
    "--negative": "#b07070",
    "--watch": "#c09050",
  },
  slate: {
    "--bg": "#181b22",
    "--bg2": "#20252e99",
    "--card": "#20252e",
    "--panel": "#282e38",
    "--text": "#d4d8e4",
    "--muted": "#606878",
    "--border": "#303848",
    "--border-subtle": "#303848",
    "--accent": "#6090c0",
    "--positive": "#5aa87a",
    "--negative": "#a87060",
    "--watch": "#a89050",
  },
  mist: {
    "--bg": "#1c2028",
    "--bg2": "#242a34",
    "--card": "#242a34",
    "--panel": "#2c3240",
    "--text": "#d0d4de",
    "--muted": "#5c6270",
    "--border": "#323848",
    "--border-subtle": "#323848",
    "--accent": "#7890a8",
    "--positive": "#5a9878",
    "--negative": "#a07068",
    "--watch": "#a08858",
  },
};

/** Apply Board/engine skin tokens to the parent React chrome (not marketing pages). */
export function applyPlatformSkin(id: string, { persist = true }: { persist?: boolean } = {}) {
  const vars = SKIN_VARS[id] || SKIN_VARS.canvas;
  const root = document.documentElement;
  Object.entries(vars).forEach(([key, value]) => {
    root.style.setProperty(key, value);
  });
  if (!persist) return;
  try {
    localStorage.setItem("smpl-skin", id);
  } catch {
    /* ignore */
  }
}

export function readSavedPlatformSkin(): string {
  let saved = "canvas";
  try {
    saved = localStorage.getItem("smpl-skin") || "canvas";
  } catch {
    /* ignore */
  }
  return SKIN_VARS[saved] ? saved : "canvas";
}

/** Hydrate parent chrome from localStorage (same key as iframe SMPLSkin). */
export function hydratePlatformSkin(): string {
  const saved = readSavedPlatformSkin();
  applyPlatformSkin(saved, { persist: false });
  return saved;
}

export function PlatformSkinSelect({ className }: { className?: string }) {
  const [skin, setSkin] = useState("canvas");

  useEffect(() => {
    setSkin(hydratePlatformSkin());
  }, []);

  return (
    <select
      className={className ?? "platform-skin-select"}
      aria-label="Design skin"
      value={skin}
      onChange={(e) => {
        const next = e.target.value;
        setSkin(next);
        applyPlatformSkin(next);
      }}
    >
      {SKINS.map((s) => (
        <option key={s.id} value={s.id}>
          {s.label}
        </option>
      ))}
    </select>
  );
}
