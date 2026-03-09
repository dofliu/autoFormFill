import { get, post, put, del } from "./client";
import type {
  EntityRelation,
  EntityRelationCreate,
  EntityRelationUpdate,
  GraphData,
} from "../types/entityRelation";

const base = (userId: number) => `/users/${userId}/entity-relations`;

// --- CRUD ---

export const createRelation = (userId: number, data: EntityRelationCreate) =>
  post<EntityRelation>(`${base(userId)}/`, data);

export const listRelations = (
  userId: number,
  relationshipType?: string,
  entityId?: number,
) => {
  const params = new URLSearchParams();
  if (relationshipType) params.set("relation_type", relationshipType);
  if (entityId !== undefined) params.set("entity_id", String(entityId));
  const qs = params.toString();
  return get<EntityRelation[]>(`${base(userId)}/${qs ? `?${qs}` : ""}`);
};

export const getRelation = (userId: number, relationId: number) =>
  get<EntityRelation>(`${base(userId)}/${relationId}`);

export const updateRelation = (
  userId: number,
  relationId: number,
  data: EntityRelationUpdate,
) => put<EntityRelation>(`${base(userId)}/${relationId}`, data);

export const deleteRelation = (userId: number, relationId: number) =>
  del(`${base(userId)}/${relationId}`);

// --- Graph queries ---

export const getFullGraph = (userId: number) =>
  get<GraphData>(`${base(userId)}/graph`);

export const getNeighborGraph = (userId: number, entityId: number) =>
  get<GraphData>(`${base(userId)}/graph/${entityId}`);

export const getRelationTypes = (userId: number) =>
  get<string[]>(`${base(userId)}/types`);
