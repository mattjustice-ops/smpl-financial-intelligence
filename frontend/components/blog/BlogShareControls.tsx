"use client";

import { Check, Link2, Linkedin } from "lucide-react";
import { useCallback, useState } from "react";

type BlogShareControlsProps = {
  title: string;
  url: string;
};

function XLogo({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      className={className}
      fill="currentColor"
    >
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.744l7.527-8.651L1.5 2.25H8.08l4.253 5.622L18.244 2.25zm-1.161 17.52h1.833L7.084 4.126H5.117L17.083 19.77z" />
    </svg>
  );
}

const buttonClass =
  "inline-flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/[0.03] text-slate-300 transition hover:border-teal-400/40 hover:bg-white/[0.06] hover:text-teal-200";

export function BlogShareControls({ title, url }: BlogShareControlsProps) {
  const [copied, setCopied] = useState(false);

  const copyLink = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers / denied clipboard
      const input = document.createElement("input");
      input.value = url;
      document.body.appendChild(input);
      input.select();
      document.execCommand("copy");
      document.body.removeChild(input);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    }
  }, [url]);

  const linkedInUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`;
  const xUrl = `https://twitter.com/intent/tweet?url=${encodeURIComponent(url)}&text=${encodeURIComponent(title)}`;

  return (
    <div className="flex flex-wrap items-center gap-3">
      <span className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
        Share
      </span>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={copyLink}
          className={buttonClass}
          aria-label={copied ? "Link copied" : "Copy link"}
          title={copied ? "Copied" : "Copy link"}
        >
          {copied ? (
            <Check className="h-4 w-4 text-teal-300" aria-hidden />
          ) : (
            <Link2 className="h-4 w-4" aria-hidden />
          )}
        </button>
        <a
          href={linkedInUrl}
          target="_blank"
          rel="noopener noreferrer"
          className={buttonClass}
          aria-label="Share on LinkedIn"
          title="Share on LinkedIn"
        >
          <Linkedin className="h-4 w-4" aria-hidden />
        </a>
        <a
          href={xUrl}
          target="_blank"
          rel="noopener noreferrer"
          className={buttonClass}
          aria-label="Share on X"
          title="Share on X"
        >
          <XLogo className="h-3.5 w-3.5" />
        </a>
      </div>
    </div>
  );
}
