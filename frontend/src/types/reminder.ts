export interface Reminder {
  id: number;
  user_id: number;
  reminder_type: string;
  title: string;
  message: string;
  related_id: string;
  status: string;
  priority: string;
  due_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReminderCreate {
  reminder_type?: string;
  title: string;
  message?: string;
  related_id?: string;
  priority?: string;
  due_date?: string;
}

export interface ReminderUpdate {
  title?: string;
  message?: string;
  status?: string;
  priority?: string;
}

export interface FillDiffItem {
  field_name: string;
  old_value: string;
  new_value: string;
}

export interface FillDiffResult {
  template_filename: string;
  previous_job_id: string;
  current_job_id: string;
  diffs: FillDiffItem[];
  total_diffs: number;
}
