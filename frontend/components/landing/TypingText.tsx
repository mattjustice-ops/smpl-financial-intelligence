"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";

export function TypingText({
  text,
  className = "",
  speedMs = 28,
}: {
  text: string;
  className?: string;
  speedMs?: number;
}) {
  const [displayed, setDisplayed] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    setDisplayed("");
    setDone(false);
    let i = 0;
    const id = window.setInterval(() => {
      i += 1;
      setDisplayed(text.slice(0, i));
      if (i >= text.length) {
        window.clearInterval(id);
        setDone(true);
      }
    }, speedMs);
    return () => window.clearInterval(id);
  }, [text, speedMs]);

  return (
    <p className={className}>
      {displayed}
      {!done && (
        <motion.span
          className="ml-0.5 inline-block h-4 w-0.5 bg-teal-400 align-middle"
          animate={{ opacity: [1, 0] }}
          transition={{ duration: 0.6, repeat: Infinity }}
        />
      )}
    </p>
  );
}
