import { useCallback, useEffect, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
} from 'reactflow';
import type {
  Node,
  Edge,
  Connection,
  NodeTypes,
  EdgeTypes,
} from 'reactflow';
import AgentNode from './AgentNode';
import AnimatedEdge from './AnimatedEdge';
import DemoControls from './DemoControls';
import { onEvent } from '../lib/relayClient';
import type { AgentNodeData, ContextPacket, RelayEvent } from '../types/relay';

const nodeTypes: NodeTypes = {
  agent: AgentNode,
};

const edgeTypes: EdgeTypes = {
  animated: AnimatedEdge,
};

// Initial nodes (stable IDs as per CLAUDE.md)
const initialNodes: Node<AgentNodeData>[] = [
  {
    id: 'analyzer',
    type: 'agent',
    position: { x: 100, y: 200 },
    data: {
      label: 'Analyzer',
      subtitle: 'Extracts key insights',
      active: false,
    },
  },
  {
    id: 'designer',
    type: 'agent',
    position: { x: 450, y: 200 },
    data: {
      label: 'Question Designer',
      subtitle: 'Generates interview questions',
      active: false,
    },
  },
  {
    id: 'evaluator',
    type: 'agent',
    position: { x: 800, y: 200 },
    data: {
      label: 'Evaluator',
      subtitle: 'Scores question quality',
      active: false,
    },
  },
];

// Initial edges (stable IDs as per CLAUDE.md)
const initialEdges: Edge[] = [
  {
    id: 'a-b',
    source: 'analyzer',
    target: 'designer',
    type: 'animated',
    data: { animated: false },
  },
  {
    id: 'b-c',
    source: 'designer',
    target: 'evaluator',
    type: 'animated',
    data: { animated: false },
  },
];

export default function InterviewRelayFlow() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [contextPacket, setContextPacket] = useState<ContextPacket>({});
  const [currentContextId, setCurrentContextId] = useState<string>('');

  // Handle new connections (if needed for future expansion)
  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  // Listen for reset events
  useEffect(() => {
    const handleReset = () => {
      // Reset all nodes to initial state
      setNodes(initialNodes);
      setEdges(initialEdges);
      setContextPacket({});
      setCurrentContextId('');
    };

    window.addEventListener('resetFlow', handleReset);
    return () => window.removeEventListener('resetFlow', handleReset);
  }, [setNodes, setEdges]);

  // Subscribe to relay events
  useEffect(() => {
    const unsubscribe = onEvent((event: RelayEvent) => {
      console.log('Received event:', event);

      switch (event.type) {
        case 'contextInitialized':
          setCurrentContextId(event.contextId);
          setContextPacket(event.packet);
          // Activate analyzer node and set its input
          updateNodeInputOutput('analyzer', event.packet.input, null);
          activateNode('analyzer');
          break;

        case 'relaySent':
          // Animate the edge with label
          const label = getEdgeLabel(event.from, event.to);
          animateEdge(event.from, event.to, true, label);
          break;

        case 'relayReceived':
          // Update packet and node data
          setContextPacket(event.packet);
          updateNodeInputOutput(event.to, getNodeInput(event.to, event.packet), getNodeOutput(event.to, event.packet));

          // Stop edge animation and deactivate node after a short delay
          setTimeout(() => {
            animateEdge(getPreviousNode(event.to), event.to, false);
            deactivateAllNodes();
          }, 1000);
          break;

        case 'contextUpdated':
          setContextPacket(event.packet);
          break;
      }
    });

    return unsubscribe;
  }, []);

  // Node activation helpers
  const activateNode = (nodeId: string) => {
    setNodes((nds) =>
      nds.map((node) => ({
        ...node,
        data: {
          ...node.data,
          active: node.id === nodeId,
        },
      }))
    );
  };

  const deactivateAllNodes = () => {
    setNodes((nds) =>
      nds.map((node) => ({
        ...node,
        data: {
          ...node.data,
          active: false,
        },
      }))
    );
  };

  const updateNodeInputOutput = (nodeId: string, inputData: any, outputData: any) => {
    setNodes((nds) =>
      nds.map((node) =>
        node.id === nodeId
          ? {
              ...node,
              data: {
                ...node.data,
                inputData,
                outputData,
              },
            }
          : node
      )
    );
  };

  const getNodeInput = (nodeId: string, packet: ContextPacket): any => {
    switch (nodeId) {
      case 'analyzer':
        return packet.input;
      case 'designer':
        return packet.analyzerOutput;
      case 'evaluator':
        return packet.designerOutput;
      default:
        return null;
    }
  };

  const getNodeOutput = (nodeId: string, packet: ContextPacket): any => {
    switch (nodeId) {
      case 'analyzer':
        return packet.analyzerOutput;
      case 'designer':
        return packet.designerOutput;
      case 'evaluator':
        return packet.evaluatorOutput;
      default:
        return null;
    }
  };

  const animateEdge = (from: string, to: string, animated: boolean, label?: string) => {
    const edgeId = getEdgeId(from, to);
    setEdges((eds) =>
      eds.map((edge) =>
        edge.id === edgeId
          ? {
              ...edge,
              data: { ...edge.data, animated, label: animated ? label : '' },
            }
          : edge
      )
    );
  };

  const getEdgeLabel = (from: string, to: string): string => {
    if (from === 'analyzer' && to === 'designer') {
      return '📊 Analysis Data';
    }
    if (from === 'designer' && to === 'evaluator') {
      return '❓ Interview Questions';
    }
    return '';
  };

  const getEdgeId = (from: string, to: string): string => {
    if (from === 'analyzer' && to === 'designer') return 'a-b';
    if (from === 'designer' && to === 'evaluator') return 'b-c';
    return '';
  };

  const getPreviousNode = (nodeId: string): string => {
    if (nodeId === 'designer') return 'analyzer';
    if (nodeId === 'evaluator') return 'designer';
    return '';
  };

  // Log context packet to console whenever it updates
  useEffect(() => {
    if (Object.keys(contextPacket).length > 0) {
      console.log('📦 Context Packet Updated:', contextPacket);
    }
  }, [contextPacket]);

  return (
    <div className="w-full h-full bg-slate-900">
      <DemoControls />
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        className="bg-slate-900"
      >
        <Background color="#475569" gap={16} />
        <Controls className="bg-slate-800 border-slate-700" />
        <MiniMap
          nodeColor="#1e293b"
          maskColor="rgba(15, 23, 42, 0.8)"
          className="bg-slate-800 border-slate-700"
        />
      </ReactFlow>
    </div>
  );
}
