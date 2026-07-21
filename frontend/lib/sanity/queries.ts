import { groq } from "next-sanity";

export const postsListQuery = groq`
  *[_type == "post" && defined(slug.current)] | order(publishedAt desc) {
    _id,
    title,
    "slug": slug.current,
    excerpt,
    publishedAt,
    mainImage,
    "author": author->{ name, role, image },
    "categories": categories[]->{ title, "slug": slug.current }
  }
`;

export const postBySlugQuery = groq`
  *[_type == "post" && slug.current == $slug][0] {
    _id,
    title,
    "slug": slug.current,
    excerpt,
    publishedAt,
    body,
    mainImage,
    seoTitle,
    seoDescription,
    "author": author->{ name, role, image },
    "categories": categories[]->{ title, "slug": slug.current }
  }
`;

export const postSlugsQuery = groq`
  *[_type == "post" && defined(slug.current)]{ "slug": slug.current }
`;

export const glossaryListQuery = groq`
  *[_type == "glossaryTerm" && defined(slug.current)] | order(term asc) {
    _id,
    term,
    "slug": slug.current,
    shortDefinition
  }
`;

export const glossaryBySlugQuery = groq`
  *[_type == "glossaryTerm" && slug.current == $slug][0] {
    _id,
    term,
    "slug": slug.current,
    shortDefinition,
    body,
    "relatedPosts": relatedPosts[]->{
      _id,
      title,
      "slug": slug.current,
      excerpt
    },
    "relatedTerms": relatedTerms[]->{
      _id,
      term,
      "slug": slug.current,
      shortDefinition
    }
  }
`;

export const glossarySlugsQuery = groq`
  *[_type == "glossaryTerm" && defined(slug.current)]{ "slug": slug.current }
`;
