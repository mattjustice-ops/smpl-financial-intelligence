import { defineArrayMember, defineField, defineType } from "sanity";

const markOptions = [
  { title: "✓ Core strength", value: "yes" },
  { title: "~ Partial / with effort", value: "partial" },
  { title: "— Not designed for", value: "no" },
];

export const comparisonTable = defineType({
  name: "comparisonTable",
  title: "Comparison table",
  type: "object",
  fields: [
    defineField({
      name: "caption",
      title: "Caption",
      type: "string",
      description: "Optional accessible label for the table.",
    }),
    defineField({
      name: "columns",
      title: "Columns",
      type: "array",
      of: [defineArrayMember({ type: "string" })],
      validation: (rule) => rule.required().min(1),
    }),
    defineField({
      name: "rows",
      title: "Rows",
      type: "array",
      of: [
        defineArrayMember({
          type: "object",
          name: "comparisonRow",
          fields: [
            defineField({
              name: "capability",
              title: "Capability",
              type: "string",
              validation: (rule) => rule.required(),
            }),
            defineField({
              name: "marks",
              title: "Marks",
              type: "array",
              description:
                "One mark per column, in the same order as Columns.",
              of: [
                defineArrayMember({
                  type: "string",
                  options: { list: markOptions },
                }),
              ],
              validation: (rule) => rule.required().min(1),
            }),
          ],
          preview: {
            select: { title: "capability" },
          },
        }),
      ],
      validation: (rule) => rule.required().min(1),
    }),
    defineField({
      name: "showLegend",
      title: "Show legend",
      type: "boolean",
      initialValue: true,
    }),
  ],
  preview: {
    select: {
      caption: "caption",
      columns: "columns",
      rows: "rows",
    },
    prepare({ caption, columns, rows }) {
      const colCount = Array.isArray(columns) ? columns.length : 0;
      const rowCount = Array.isArray(rows) ? rows.length : 0;
      return {
        title: caption || "Comparison table",
        subtitle: `${rowCount} rows × ${colCount} columns`,
      };
    },
  },
});
