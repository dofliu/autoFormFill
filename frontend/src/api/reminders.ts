import { get, post, put, del } from "./client";
import type {
  Reminder,
  ReminderCreate,
  ReminderUpdate,
  FillDiffResult,
} from "../types/reminder";

const basePath = (userId: number) => `/users/${userId}/reminders`;

export async function createReminder(
  userId: number,
  data: ReminderCreate,
): Promise<Reminder> {
  return post<Reminder>(basePath(userId) + "/", data);
}

export async function listReminders(
  userId: number,
  options?: { status?: string; reminder_type?: string; limit?: number },
): Promise<Reminder[]> {
  const params = new URLSearchParams();
  if (options?.status) params.set("status", options.status);
  if (options?.reminder_type) params.set("reminder_type", options.reminder_type);
  if (options?.limit) params.set("limit", String(options.limit));
  const qs = params.toString();
  return get<Reminder[]>(basePath(userId) + "/" + (qs ? `?${qs}` : ""));
}

export async function countActive(
  userId: number,
): Promise<{ count: number }> {
  return get<{ count: number }>(`${basePath(userId)}/count`);
}

export async function getReminder(
  userId: number,
  reminderId: number,
): Promise<Reminder> {
  return get<Reminder>(`${basePath(userId)}/${reminderId}`);
}

export async function updateReminder(
  userId: number,
  reminderId: number,
  data: ReminderUpdate,
): Promise<Reminder> {
  return put<Reminder>(
    `${basePath(userId)}/${reminderId}`,
    data,
  );
}

export async function dismissAll(
  userId: number,
): Promise<{ dismissed: number }> {
  return post<{ dismissed: number }>(
    `${basePath(userId)}/dismiss-all`,
    {},
  );
}

export async function deleteReminder(
  userId: number,
  reminderId: number,
): Promise<void> {
  await del(`${basePath(userId)}/${reminderId}`);
}

export async function getFillDiff(
  userId: number,
  jobId: string,
): Promise<FillDiffResult> {
  return get<FillDiffResult>(
    `${basePath(userId)}/fill-diff/${jobId}`,
  );
}
