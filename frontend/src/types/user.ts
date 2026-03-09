export interface UserProfile {
  id: number;
  name_zh: string | null;
  name_en: string | null;
  title: string | null;
  department: string | null;
  university: string | null;
  email: string | null;
  phone_office: string | null;
  address: string | null;
}

export interface UserProfileCreate {
  name_zh?: string | null;
  name_en?: string | null;
  title?: string | null;
  department?: string | null;
  university?: string | null;
  email?: string | null;
  phone_office?: string | null;
  address?: string | null;
}

export type UserProfileUpdate = UserProfileCreate;
