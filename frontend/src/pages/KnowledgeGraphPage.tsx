import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import type { ForceGraphMethods } from "react-force-graph-2d";
import * as entityRelationsApi from "../api/entityRelations";
import * as entitiesApi from "../api/entities";
import AddRelationModal from "../components/AddRelationModal";
import type { Entity } from "../types/entity";
import type { GraphData, GraphNode } from "../types/entityRelation";

// --- Color mapping by entity_type ---
const TYPE_COLORS: Record<string, string> = {
  person: "#3b82f6",       // blue
  organization: "#22c55e", // green
  project: "#a855f7",      // purple
};
const DEFAULT_COLOR = "#6b7280"; // gray

function getNodeColor(entityType: string): string {
  return TYPE_COLORS[entityType] ?? DEFAULT_COLOR;
}

const TYPE_LABELS: Record<string, string> = {
  person: "人員",
  organization: "組織",
  project: "專案",
};

export default function KnowledgeGraphPage() {
  const userId = Number(localStorage.getItem("smartfill_user_id") || "1");
  const containerRef = useRef<HTMLDivElement>(null);
  const fgRef = useRef<ForceGraphMethods | undefined>(undefined);

  // Data
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], edges: [] });
  const [entities, setEntities] = useState<Entity[]>([]);
  const [relationTypes, setRelationTypes] = useState<string[]>([]);

  // Filters
  const [filterEntityType, setFilterEntityType] = useState("");
  const [filterRelationType, setFilterRelationType] = useState("");

  // Selected node
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [nodeRelations, setNodeRelations] = useState<{
    from: { id: number; target: string; type: string }[];
    to: { id: number; source: string; type: string }[];
  }>({ from: [], to: [] });

  // Modal
  const [showAddModal, setShowAddModal] = useState(false);
  const [addSourceId, setAddSourceId] = useState<number | undefined>();

  // Dimensions
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  // Load data
  const loadGraph = useCallback(async () => {
    const [graph, ents, types] = await Promise.all([
      entityRelationsApi.getFullGraph(userId),
      entitiesApi.listEntities(userId),
      entityRelationsApi.getRelationTypes(userId),
    ]);
    setGraphData(graph);
    setEntities(ents);
    setRelationTypes(types);
  }, [userId]);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  // Resize observer
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setDimensions({
          width: entry.contentRect.width,
          height: entry.contentRect.height,
        });
      }
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // Filtered graph data — transform to react-force-graph format
  const filteredData = useMemo(() => {
    let nodes = graphData.nodes;
    let edges = graphData.edges;

    if (filterEntityType) {
      const typeNodeIds = new Set(
        nodes.filter((n) => n.entity_type === filterEntityType).map((n) => n.id)
      );
      nodes = nodes.filter((n) => typeNodeIds.has(n.id));
      edges = edges.filter(
        (e) => typeNodeIds.has(e.source) && typeNodeIds.has(e.target)
      );
    }

    if (filterRelationType) {
      edges = edges.filter((e) => e.relation_type === filterRelationType);
      // Keep only nodes that have at least one visible edge
      const connectedIds = new Set<number>();
      for (const e of edges) {
        connectedIds.add(e.source);
        connectedIds.add(e.target);
      }
      nodes = nodes.filter((n) => connectedIds.has(n.id));
    }

    return {
      nodes: nodes.map((n) => ({ ...n })),
      links: edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        relation_type: e.relation_type,
        description: e.description ?? "",
      })),
    };
  }, [graphData, filterEntityType, filterRelationType]);

  // Zoom to fit after data loads
  useEffect(() => {
    if (filteredData.nodes.length > 0 && fgRef.current) {
      setTimeout(() => fgRef.current?.zoomToFit(400, 50), 300);
    }
  }, [filteredData]);

  // Node click handler
  const handleNodeClick = useCallback(
    (node: { id?: string | number; entity_type?: string; name?: string }) => {
      const gNode = graphData.nodes.find((n) => n.id === node.id);
      if (!gNode) return;
      setSelectedNode(gNode);

      // Compute connections
      const from = graphData.edges
        .filter((e) => e.source === gNode.id)
        .map((e) => ({
          id: e.id,
          target: graphData.nodes.find((n) => n.id === e.target)?.name ?? `#${e.target}`,
          type: e.relation_type,
        }));
      const to = graphData.edges
        .filter((e) => e.target === gNode.id)
        .map((e) => ({
          id: e.id,
          source: graphData.nodes.find((n) => n.id === e.source)?.name ?? `#${e.source}`,
          type: e.relation_type,
        }));
      setNodeRelations({ from, to });
    },
    [graphData],
  );

  const handleAddRelation = (sourceId?: number) => {
    setAddSourceId(sourceId);
    setShowAddModal(true);
  };

  const handleSaveRelation = async (data: Parameters<typeof entityRelationsApi.createRelation>[1]) => {
    await entityRelationsApi.createRelation(userId, data);
    await loadGraph();
  };

  const handleDeleteRelation = async (relationId: number) => {
    await entityRelationsApi.deleteRelation(userId, relationId);
    setSelectedNode(null);
    await loadGraph();
  };

  // Custom node rendering on canvas
  const paintNode = useCallback(
    (node: { id?: string | number; x?: number; y?: number; entity_type?: string; name?: string }, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const x = node.x ?? 0;
      const y = node.y ?? 0;
      const label = node.name ?? "";
      const fontSize = Math.max(12 / globalScale, 2);
      const radius = 5;

      // Circle
      ctx.beginPath();
      ctx.arc(x, y, radius, 0, 2 * Math.PI, false);
      ctx.fillStyle = getNodeColor(node.entity_type ?? "");
      ctx.fill();

      // Border highlight for selected
      if (selectedNode && node.id === selectedNode.id) {
        ctx.strokeStyle = "#f97316";
        ctx.lineWidth = 2 / globalScale;
        ctx.stroke();
      }

      // Label
      ctx.font = `${fontSize}px sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      ctx.fillStyle = "#374151";
      ctx.fillText(label, x, y + radius + 2 / globalScale);
    },
    [selectedNode],
  );

  const entityTypeOptions = useMemo(() => {
    const types = new Set(graphData.nodes.map((n) => n.entity_type));
    return Array.from(types).sort();
  }, [graphData]);

  return (
    <div className="flex h-full">
      {/* Graph area */}
      <div className="flex-1 flex flex-col">
        {/* Toolbar */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-200 bg-white">
          <h2 className="text-lg font-semibold text-gray-800">知識圖譜</h2>

          <select
            className="border border-gray-300 rounded-lg px-2 py-1.5 text-sm"
            value={filterEntityType}
            onChange={(e) => setFilterEntityType(e.target.value)}
          >
            <option value="">全部類型</option>
            {entityTypeOptions.map((t) => (
              <option key={t} value={t}>
                {TYPE_LABELS[t] ?? t}
              </option>
            ))}
          </select>

          <select
            className="border border-gray-300 rounded-lg px-2 py-1.5 text-sm"
            value={filterRelationType}
            onChange={(e) => setFilterRelationType(e.target.value)}
          >
            <option value="">全部關係</option>
            {relationTypes.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>

          <button
            onClick={() => handleAddRelation()}
            className="ml-auto px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
          >
            + 新增關係
          </button>

          <button
            onClick={() => fgRef.current?.zoomToFit(400, 50)}
            className="px-3 py-1.5 border border-gray-300 text-sm rounded-lg hover:bg-gray-50 transition-colors"
          >
            適配視圖
          </button>
        </div>

        {/* Graph canvas */}
        <div ref={containerRef} className="flex-1 relative bg-gray-50">
          {filteredData.nodes.length === 0 ? (
            <div className="flex items-center justify-center h-full text-gray-400 text-sm">
              {graphData.nodes.length === 0
                ? "尚無實體資料，請先至「實體管理」新增實體"
                : "篩選條件下無結果"}
            </div>
          ) : (
            <ForceGraph2D
              ref={fgRef}
              width={dimensions.width}
              height={dimensions.height}
              graphData={filteredData}
              nodeId="id"
              linkSource="source"
              linkTarget="target"
              nodeCanvasObject={paintNode}
              nodeCanvasObjectMode={() => "replace"}
              linkDirectionalArrowLength={4}
              linkDirectionalArrowRelPos={0.9}
              linkColor={() => "#94a3b8"}
              linkWidth={1.5}
              linkLabel={(link) => {
                const l = link as { relation_type?: string };
                return l.relation_type ?? "";
              }}
              onNodeClick={handleNodeClick}
              onBackgroundClick={() => setSelectedNode(null)}
              cooldownTicks={80}
              enableNodeDrag={true}
            />
          )}
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 px-4 py-2 border-t border-gray-200 bg-white text-xs text-gray-500">
          {Object.entries(TYPE_COLORS).map(([type, color]) => (
            <span key={type} className="flex items-center gap-1">
              <span
                className="inline-block w-3 h-3 rounded-full"
                style={{ backgroundColor: color }}
              />
              {TYPE_LABELS[type] ?? type}
            </span>
          ))}
          <span className="ml-auto">
            節點 {filteredData.nodes.length} / 關係 {filteredData.links.length}
          </span>
        </div>
      </div>

      {/* Side panel */}
      {selectedNode && (
        <div className="w-72 border-l border-gray-200 bg-white p-4 overflow-y-auto">
          <div className="flex items-center gap-2 mb-3">
            <span
              className="inline-block w-3 h-3 rounded-full"
              style={{ backgroundColor: getNodeColor(selectedNode.entity_type) }}
            />
            <span className="text-xs text-gray-500">
              {TYPE_LABELS[selectedNode.entity_type] ?? selectedNode.entity_type}
            </span>
          </div>
          <h3 className="text-lg font-semibold text-gray-800 mb-1">
            {selectedNode.name}
          </h3>
          {selectedNode.description && (
            <p className="text-sm text-gray-600 mb-3">{selectedNode.description}</p>
          )}

          {/* Outgoing relations */}
          {nodeRelations.from.length > 0 && (
            <div className="mb-3">
              <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">
                指向 →
              </h4>
              {nodeRelations.from.map((r) => (
                <div
                  key={r.id}
                  className="flex items-center justify-between text-sm py-1 border-b border-gray-100"
                >
                  <span>
                    <span className="text-blue-600 font-medium">{r.type}</span>
                    {" → "}
                    {r.target}
                  </span>
                  <button
                    onClick={() => handleDeleteRelation(r.id)}
                    className="text-xs text-red-400 hover:text-red-600"
                  >
                    刪除
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Incoming relations */}
          {nodeRelations.to.length > 0 && (
            <div className="mb-3">
              <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">
                ← 來自
              </h4>
              {nodeRelations.to.map((r) => (
                <div
                  key={r.id}
                  className="flex items-center justify-between text-sm py-1 border-b border-gray-100"
                >
                  <span>
                    {r.source}
                    {" ──["}
                    <span className="text-blue-600 font-medium">{r.type}</span>
                    {"]──→"}
                  </span>
                  <button
                    onClick={() => handleDeleteRelation(r.id)}
                    className="text-xs text-red-400 hover:text-red-600"
                  >
                    刪除
                  </button>
                </div>
              ))}
            </div>
          )}

          {nodeRelations.from.length === 0 && nodeRelations.to.length === 0 && (
            <p className="text-sm text-gray-400 mb-3">尚無關聯</p>
          )}

          <div className="flex gap-2 mt-3">
            <button
              onClick={() => handleAddRelation(selectedNode.id)}
              className="flex-1 px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
            >
              新增關係
            </button>
            <a
              href="/entities"
              className="flex-1 px-3 py-1.5 border border-gray-300 text-sm rounded-lg hover:bg-gray-50 text-center"
            >
              查看實體
            </a>
          </div>
        </div>
      )}

      {/* Add relation modal */}
      <AddRelationModal
        open={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSave={handleSaveRelation}
        entities={entities}
        sourceEntityId={addSourceId}
        existingTypes={relationTypes}
      />
    </div>
  );
}
