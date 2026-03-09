export interface ComplianceRule {
  id: number;
  user_id: number;
  rule_name: string;
  field_pattern: string;
  rule_type: string;
  rule_value: string;
  severity: string;
  message: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ComplianceRuleCreate {
  rule_name: string;
  field_pattern?: string;
  rule_type: string;
  rule_value?: string;
  severity?: string;
  message?: string;
}

export interface ComplianceRuleUpdate {
  rule_name?: string;
  field_pattern?: string;
  rule_type?: string;
  rule_value?: string;
  severity?: string;
  message?: string;
  is_active?: boolean;
}

export interface ComplianceViolation {
  field_name: string;
  rule_name: string;
  rule_type: string;
  severity: string;
  message: string;
}

export interface ComplianceCheckResult {
  violations: ComplianceViolation[];
  total_errors: number;
  total_warnings: number;
  total_info: number;
  passed: boolean;
}
