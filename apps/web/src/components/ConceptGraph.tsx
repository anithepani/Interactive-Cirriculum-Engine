"use client";

import { useMemo, useEffect } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

interface Concept {
  id: number;
  label: string;
  difficulty: number;
}

interface ConceptEdge {
  id: number;
  source_id: number;
  target_id: number;
  relation: string;
}

interface ConceptGraphProps {
  nodes: Concept[];
  edges: ConceptEdge[];
}

import useSWR from 'swr';
import { authFetcher } from '@/lib/auth';
import LoadingSpinner from './LoadingSpinner';

export default function ConceptGraph({ curriculumId }: { curriculumId: number }) {
  const { data, error, isLoading } = useSWR<{ nodes: Concept[], edges: ConceptEdge[] }>(
    `/api/v1/curricula/${curriculumId}/graph`,
    authFetcher
  );

  const initialNodes = data?.nodes || [];
  const initialEdges = data?.edges || [];
  // Simple layout logic for now, or we could use dagre for auto-layout.
  // We'll just scatter them horizontally/vertically.
  const layoutedNodes = useMemo(() => {
    return initialNodes.map((node, index) => {
      // Very basic grid layout
      const x = (index % 3) * 250;
      const y = Math.floor(index / 3) * 150;
      return {
        id: node.id.toString(),
        position: { x, y },
        data: { label: node.label },
        style: {
          background: '#fff',
          border: '1px solid #e2e8f0',
          borderRadius: '8px',
          padding: '12px',
          fontSize: '14px',
          fontWeight: 600,
          color: '#1e293b',
          boxShadow: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
          width: 180,
        },
      };
    });
  }, [initialNodes]);

  const layoutedEdges = useMemo(() => {
    return initialEdges.map((edge) => ({
      id: edge.id.toString(),
      source: edge.source_id.toString(),
      target: edge.target_id.toString(),
      animated: true,
      label: edge.relation,
      style: { stroke: '#94a3b8', strokeWidth: 2 },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: '#94a3b8',
      },
    }));
  }, [initialEdges]);

  const [nodes, setNodes, onNodesChange] = useNodesState(layoutedNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(layoutedEdges);

  // Update state when data arrives
  useEffect(() => {
    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
  }, [layoutedNodes, layoutedEdges, setNodes, setEdges]);

  if (isLoading) {
    return (
      <div className="flex h-[600px] items-center justify-center bg-slate-50 dark:bg-zinc-900 rounded-xl border border-ink/10">
        <LoadingSpinner size={32} />
      </div>
    );
  }

  if (nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full w-full bg-slate-50 dark:bg-zinc-900 rounded-xl border border-ink/10">
        <p className="text-ink-soft">No concepts available for this curriculum.</p>
      </div>
    );
  }

  return (
    <div className="w-full h-[600px] border border-ink/10 rounded-xl overflow-hidden bg-slate-50 dark:bg-zinc-900">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        attributionPosition="bottom-right"
      >
        <MiniMap 
          nodeStrokeColor={(n) => {
            return '#e2e8f0';
          }}
          nodeColor={(n) => {
            return '#fff';
          }}
        />
        <Controls />
        <Background color="#cbd5e1" gap={16} />
      </ReactFlow>
    </div>
  );
}
