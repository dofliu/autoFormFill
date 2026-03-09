import { get, post, put, del } from "./client";
import type { Entity, EntityCreate, EntityUpdate } from "../types/entity";

export const listEntities = (userId: number, entityType?: string) => {
  const params = entityType ? `?entity_type=${encodeURIComponent(entityType)}` : "";
  return get<Entity[]>(`/users/${userId}/entities/${params}`);
};

export const getEntity = (userId: number, entityId: number) =>
  get<Entity>(`/users/${userId}/entities/${entityId}`);

export const createEntity = (userId: number, data: EntityCreate) =>
  post<Entity>(`/users/${userId}/entities/`, data);

export const updateEntity = (userId: number, entityId: number, data: EntityUpdate) =>
  put<Entity>(`/users/${userId}/entities/${entityId}`, data);

export const deleteEntity = (userId: number, entityId: number) =>
  del(`/users/${userId}/entities/${entityId}`);
