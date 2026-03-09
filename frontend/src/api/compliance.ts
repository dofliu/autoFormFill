import { get, post, put, del } from "./client";
import type {
  ComplianceRule,
  ComplianceRuleCreate,
  ComplianceRuleUpdate,
  ComplianceCheckResult,
} from "../types/compliance";

const basePath = (userId: number) =>
  `/users/${userId}/compliance-rules`;

export async function createRule(
  userId: number,
  data: ComplianceRuleCreate,
): Promise<ComplianceRule> {
  return post<ComplianceRule>(basePath(userId) + "/", data);
}

export async function listRules(
  userId: number,
  activeOnly = false,
): Promise<ComplianceRule[]> {
  const params = activeOnly ? "?active_only=true" : "";
  return get<ComplianceRule[]>(basePath(userId) + "/" + params);
}

export async function getRule(
  userId: number,
  ruleId: number,
): Promise<ComplianceRule> {
  return get<ComplianceRule>(`${basePath(userId)}/${ruleId}`);
}

export async function updateRule(
  userId: number,
  ruleId: number,
  data: ComplianceRuleUpdate,
): Promise<ComplianceRule> {
  return put<ComplianceRule>(`${basePath(userId)}/${ruleId}`, data);
}

export async function deleteRule(
  userId: number,
  ruleId: number,
): Promise<void> {
  await del(`${basePath(userId)}/${ruleId}`);
}

export async function checkJobCompliance(
  userId: number,
  jobId: string,
): Promise<ComplianceCheckResult> {
  return post<ComplianceCheckResult>(
    `${basePath(userId)}/check/${jobId}`,
    {},
  );
}
