export interface Entity {
  id: number;
  user_id: number;
  entity_type: string;
  name: string;
  description: string;
  attributes: Record<string, string>;
  created_at: string;
  updated_at: string;
}

export interface EntityCreate {
  entity_type: string;
  name: string;
  description?: string;
  attributes?: Record<string, string>;
}

export type EntityUpdate = Partial<EntityCreate>;
