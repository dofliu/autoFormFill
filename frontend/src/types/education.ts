export type EntryType = "Education" | "Experience";

export interface EducationExperience {
  id: number;
  user_id: number;
  type: EntryType;
  organization: string | null;
  role_degree: string | null;
  start_date: string | null;
  end_date: string | null;
}

export interface EducationExperienceCreate {
  type: EntryType;
  organization?: string | null;
  role_degree?: string | null;
  start_date?: string | null;
  end_date?: string | null;
}

export interface EducationExperienceUpdate {
  type?: EntryType | null;
  organization?: string | null;
  role_degree?: string | null;
  start_date?: string | null;
  end_date?: string | null;
}
