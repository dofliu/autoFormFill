import { get, post, put, del } from "./client";
import type {
  EducationExperience,
  EducationExperienceCreate,
  EducationExperienceUpdate,
} from "../types/education";

export const listEntries = (userId: number) =>
  get<EducationExperience[]>(`/users/${userId}/education/`);

export const createEntry = (userId: number, data: EducationExperienceCreate) =>
  post<EducationExperience>(`/users/${userId}/education/`, data);

export const updateEntry = (userId: number, entryId: number, data: EducationExperienceUpdate) =>
  put<EducationExperience>(`/users/${userId}/education/${entryId}`, data);

export const deleteEntry = (userId: number, entryId: number) =>
  del(`/users/${userId}/education/${entryId}`);
