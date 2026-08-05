type FaqJsonLdProps = {
  items: Array<{ question: string; answer: string }>;
};

/** FAQPage JSON-LD for blog posts that include an on-page FAQ section. */
export function FaqJsonLd({ items }: FaqJsonLdProps) {
  if (!items.length) return null;

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: items.map((item) => ({
      "@type": "Question",
      name: item.question,
      acceptedAnswer: {
        "@type": "Answer",
        text: item.answer,
      },
    })),
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
    />
  );
}
