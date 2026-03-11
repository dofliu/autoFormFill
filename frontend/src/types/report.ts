/** Request body sent to POST /api/v1/report/generate. */
export interface ReportRequest {
  topic: string;
  report_type?: "summary" | "detailed" | "executive";
  target_audience?: "academic" | "business" | "general";
  sections?: string[];
  language?: "zh-TW" | "en";
  collections?: string[];
  n_results?: number;
  user_id?: number;
}
