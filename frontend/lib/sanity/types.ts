import type { PortableTextBlock } from "@portabletext/types";

export type SanityImage = {
  _type?: "image";
  asset?: { _ref?: string; _type?: string };
  alt?: string;
};

export type SanityAuthor = {
  name: string;
  role?: string | null;
  image?: SanityImage | null;
};

export type SanityCategory = {
  title: string;
  slug: string;
};

export type SanityPostListItem = {
  _id: string;
  title: string;
  slug: string;
  excerpt?: string | null;
  publishedAt?: string | null;
  mainImage?: SanityImage | null;
  author?: SanityAuthor | null;
  categories?: SanityCategory[] | null;
};

export type SanityPost = SanityPostListItem & {
  body?: PortableTextBlock[] | null;
  seoTitle?: string | null;
  seoDescription?: string | null;
};

export type SanityGlossaryListItem = {
  _id: string;
  term: string;
  slug: string;
  shortDefinition: string;
};

export type SanityGlossaryTerm = SanityGlossaryListItem & {
  body?: PortableTextBlock[] | null;
  relatedPosts?: Array<{
    _id: string;
    title: string;
    slug: string;
    excerpt?: string | null;
  }> | null;
  relatedTerms?: Array<{
    _id: string;
    term: string;
    slug: string;
    shortDefinition: string;
  }> | null;
};
