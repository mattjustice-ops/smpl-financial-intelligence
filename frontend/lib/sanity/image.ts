import imageUrlBuilder from "@sanity/image-url";

import { dataset, isSanityConfigured, projectId } from "./client";

type SanityImageSource = Parameters<
  ReturnType<typeof imageUrlBuilder>["image"]
>[0];

const builder = isSanityConfigured()
  ? imageUrlBuilder({ projectId, dataset })
  : null;

export function urlForImage(source: SanityImageSource | null | undefined) {
  if (!builder || !source) return null;
  return builder.image(source);
}
