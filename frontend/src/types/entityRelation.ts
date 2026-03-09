export interface EntityRelation {
  id: number;
  user_id: number;
  from_entity_id: number;
  to_entity_id: number;
  relation_type: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface EntityRelationCreate {
  from_entity_id: number;
  to_entity_id: number;
  relation_type: string;
  description?: string;
}

export interface EntityRelationUpdate {
  relation_type?: string;
  description?: string;
}

// --- Graph visualization types ---

export interface GraphNode {
  id: number;
  name: string;
  entity_type: string;
  description?: string;
}

export interface GraphEdge {
  id: number;
  source: number;
  target: number;
  relation_type: string;
  description?: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}
