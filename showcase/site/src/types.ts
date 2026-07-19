export type Evidence = {
  gdd_path: string | null;
  gdd_line: number | null;
  code_path: string | null;
  code_line: number | null;
  code_symbol_path: string | null;
  containment_path: string[];
  gdd_excerpt: string | null;
  code_excerpt: string | null;
};

export type Finding = {
  status: string;
  tracked_entity: { name: string; entity_type: string } | null;
  code_entity: { name: string; kind: string; path: string } | null;
  evidence: Evidence | null;
};

export type Report = {
  state: "COMPLETE" | "PARTIAL";
  findings: Finding[];
  candidates: { name: string; path: string; line: number }[];
  summary: {
    coverage_percent: number | null;
    matched: number;
    total: number;
    priority_findings: { status: string; name: string }[];
  };
  warnings: { path: string; reason: string; impact: string }[];
  advisories: {
    path: string;
    code: string;
    reason: string;
    impact: string;
    next_action: string;
  }[];
};

export const statusCopy: Record<string, string> = {
  MATCHED: "Implementation found",
  MISSING: "Tracked concept has no exact implementation",
  "RENAMED?": "Possible implementation rename",
  ORPHANED: "Implementation is not represented in GDD",
  PLANNED: "Intentionally outside current slice",
};
