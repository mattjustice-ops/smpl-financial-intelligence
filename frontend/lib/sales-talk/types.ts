export type SalesAudience =
  | "cfo"
  | "it"
  | "fpa"
  | "ceo"
  | "engineer"
  | "investor"
  | "general";

export type SalesConfidence = "verified" | "directional" | "do-not-answer";

export type SalesTone = "external_safe" | "internal_deep";

export type SalesKbEntry = {
  id: string;
  title: string;
  topics: string[];
  keywords?: string[];
  answer: string;
  confidence: SalesConfidence;
  audiences?: SalesAudience[];
  tone?: SalesTone;
  source: string;
  deflect_script?: string;
};

export type SalesKbFile = {
  version?: number;
  default_deflect_script?: string;
  entries: SalesKbEntry[];
};

export type SalesTalkMatch = {
  entry: SalesKbEntry;
  score: number;
};

export type SalesTalkAnswerResponse = {
  status: "matched" | "deflect" | "no_prepared_answer";
  question: string;
  entryId: string | null;
  title: string | null;
  answer: string | null;
  confidence: SalesConfidence | null;
  source: string | null;
  tone: SalesTone | null;
  deflectScript: string;
  score: number | null;
  rephrased: boolean;
  matches?: Array<{ id: string; title: string; score: number; confidence: SalesConfidence }>;
};
