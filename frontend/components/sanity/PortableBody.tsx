"use client";

import { PortableText, type PortableTextComponents } from "@portabletext/react";
import type { PortableTextBlock } from "@portabletext/types";
import Image from "next/image";
import Link from "next/link";
import { useMemo } from "react";

import { urlForImage } from "@/lib/sanity/image";
import { portableHeadingIdByKey } from "@/lib/sanity/headings";

const baseComponents: PortableTextComponents = {
  block: {
    h2: ({ children }) => (
      <h2 className="mt-10 scroll-mt-24 text-2xl font-semibold tracking-tight text-white">
        {children}
      </h2>
    ),
    h3: ({ children }) => (
      <h3 className="mt-8 scroll-mt-24 text-xl font-semibold tracking-tight text-white">
        {children}
      </h3>
    ),
    normal: ({ children }) => (
      <p className="mt-4 text-base leading-relaxed text-slate-300">{children}</p>
    ),
    blockquote: ({ children }) => (
      <blockquote className="mt-6 border-l-2 border-teal-400/60 pl-4 text-slate-300 italic">
        {children}
      </blockquote>
    ),
  },
  list: {
    bullet: ({ children }) => (
      <ul className="mt-4 list-disc space-y-2 pl-6 text-slate-300">{children}</ul>
    ),
    number: ({ children }) => (
      <ol className="mt-4 list-decimal space-y-2 pl-6 text-slate-300">{children}</ol>
    ),
  },
  listItem: {
    bullet: ({ children }) => <li className="leading-relaxed">{children}</li>,
    number: ({ children }) => <li className="leading-relaxed">{children}</li>,
  },
  marks: {
    strong: ({ children }) => (
      <strong className="font-semibold text-white">{children}</strong>
    ),
    em: ({ children }) => <em className="italic text-slate-200">{children}</em>,
    code: ({ children }) => (
      <code className="rounded bg-white/10 px-1.5 py-0.5 font-mono text-sm text-teal-200">
        {children}
      </code>
    ),
    link: ({ children, value }) => {
      const href = (value?.href as string | undefined) || "#";
      const isExternal = /^https?:\/\//i.test(href);
      if (isExternal) {
        return (
          <a
            href={href}
            className="text-teal-300 underline decoration-teal-400/40 underline-offset-4 transition hover:text-teal-200"
            target="_blank"
            rel="noopener noreferrer"
          >
            {children}
          </a>
        );
      }
      return (
        <Link
          href={href}
          className="text-teal-300 underline decoration-teal-400/40 underline-offset-4 transition hover:text-teal-200"
        >
          {children}
        </Link>
      );
    },
  },
  types: {
    image: ({ value }) => {
      const url = urlForImage(value)?.width(1200).height(675).url();
      if (!url) return null;
      return (
        <figure className="mt-8 overflow-hidden rounded-2xl border border-white/10">
          <Image
            src={url}
            alt={value?.alt || ""}
            width={1200}
            height={675}
            className="h-auto w-full object-cover"
          />
          {value?.alt ? (
            <figcaption className="border-t border-white/10 px-4 py-2 text-sm text-slate-500">
              {value.alt}
            </figcaption>
          ) : null}
        </figure>
      );
    },
  },
};

function componentsWithHeadingAnchors(
  idByKey: Map<string, string>,
): PortableTextComponents {
  return {
    ...baseComponents,
    block: {
      normal: ({ children }) => (
        <p className="mt-4 text-base leading-relaxed text-slate-300">{children}</p>
      ),
      blockquote: ({ children }) => (
        <blockquote className="mt-6 border-l-2 border-teal-400/60 pl-4 text-slate-300 italic">
          {children}
        </blockquote>
      ),
      h2: ({ children, value }) => {
        const id = value?._key ? idByKey.get(value._key) : undefined;
        return (
          <h2
            id={id}
            className="mt-10 scroll-mt-24 text-2xl font-semibold tracking-tight text-white"
          >
            {children}
          </h2>
        );
      },
      h3: ({ children, value }) => {
        const id = value?._key ? idByKey.get(value._key) : undefined;
        return (
          <h3
            id={id}
            className="mt-8 scroll-mt-24 text-xl font-semibold tracking-tight text-white"
          >
            {children}
          </h3>
        );
      },
    },
  };
}

export function PortableBody({
  value,
  headingAnchors = false,
}: {
  value?: PortableTextBlock[] | null;
  /** When true, h2/h3 get stable slug ids for TOC / deep links. Opt-in so glossary stays unchanged. */
  headingAnchors?: boolean;
}) {
  const components = useMemo(() => {
    if (!headingAnchors || !value?.length) return baseComponents;
    return componentsWithHeadingAnchors(portableHeadingIdByKey(value));
  }, [headingAnchors, value]);

  if (!value?.length) return null;
  return (
    <div className="portable-body max-w-none">
      <PortableText value={value} components={components} />
    </div>
  );
}
