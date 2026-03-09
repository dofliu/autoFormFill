import { get, post, put, del } from "./client";
import type { UserProfile, UserProfileCreate, UserProfileUpdate } from "../types/user";

export const listUsers = () => get<UserProfile[]>("/users/");
export const getUser = (id: number) => get<UserProfile>(`/users/${id}`);
export const createUser = (data: UserProfileCreate) => post<UserProfile>("/users/", data);
export const updateUser = (id: number, data: UserProfileUpdate) => put<UserProfile>(`/users/${id}`, data);
export const deleteUser = (id: number) => del(`/users/${id}`);
