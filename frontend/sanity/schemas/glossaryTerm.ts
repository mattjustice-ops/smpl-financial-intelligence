import { defineField, defineType } from "sanity";

export const glossaryTerm = defineType({
  name: "glossaryTerm",
  title: "Glossary term",
  type: "document",
  fields: [
    defineField({
      name: "term",
      title: "Term",
      type: "string",
      validation: (rule) => rule.required(),
    }),
    defineField({
      name: "slug",
      title: "Slug",
      type: "slug",
      options: { source: "term", maxLength: 96 },
      validation: (rule) => rule.required(),
    }),
    defineField({
      name: "shortDefinition",
      title: "Short definition",
      type: "text",
      rows: 2,
      validation: (rule) => rule.required().max(320),
    }),
    defineField({
      name: "body",
      title: "Full definition",
      type: "blockContent",
    }),
    defineField({
      name: "relatedPosts",
      title: "Related posts",
      type: "array",
      of: [{ type: "reference", to: [{ type: "post" }] }],
    }),
    defineField({
      name: "relatedTerms",
      title: "Related terms",
      type: "array",
      of: [{ type: "reference", to: [{ type: "glossaryTerm" }] }],
    }),
  ],
  orderings: [
    {
      title: "Term A–Z",
      name: "termAsc",
      by: [{ field: "term", direction: "asc" }],
    },
  ],
  preview: {
    select: { title: "term", subtitle: "shortDefinition" },
  },
});
