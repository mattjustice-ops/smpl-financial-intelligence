"use client";

import dynamic from "next/dynamic";

const BoardPlatformApp = dynamic(
  () => import("@/components/board/BoardPlatformApp").then((m) => m.BoardPlatformApp),
  {
    ssr: false,
    loading: () => (
      <div style={{ padding: 24, color: "#aab8a2", background: "#18241b", minHeight: "100vh" }}>
        Loading Board Platform…
      </div>
    ),
  },
);

export default function BoardPlatformPage() {
  return <BoardPlatformApp />;
}
