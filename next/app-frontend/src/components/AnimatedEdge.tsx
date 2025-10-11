import { memo } from 'react';
import { getBezierPath } from 'reactflow';
import type { EdgeProps } from 'reactflow';

interface AnimatedEdgeProps extends EdgeProps {
  data?: {
    animated?: boolean;
    label?: string;
  };
}

function AnimatedEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
}: AnimatedEdgeProps) {
  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const animated = data?.animated ?? false;
  const label = data?.label || '';

  return (
    <>
      {/* Base edge path */}
      <path
        id={id}
        className="react-flow__edge-path"
        d={edgePath}
        strokeWidth={3}
        stroke={animated ? 'url(#cyan-gradient)' : '#475569'}
        fill="none"
        style={{
          transition: 'stroke 0.3s ease',
        }}
      />

      {/* Gradient definition */}
      <defs>
        <linearGradient id="cyan-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#22d3ee" />
          <stop offset="100%" stopColor="#3b82f6" />
        </linearGradient>
      </defs>

      {/* Animated packet with label */}
      {animated && (
        <g>
          {/* Glow effect */}
          <circle r="12" fill="rgba(34, 211, 238, 0.2)" opacity="0.6">
            <animateMotion dur="2s" repeatCount="indefinite">
              <mpath href={`#${id}`} />
            </animateMotion>
          </circle>

          {/* Main circle */}
          <circle r="6" fill="#22d3ee" className="drop-shadow-lg">
            <animateMotion dur="2s" repeatCount="indefinite">
              <mpath href={`#${id}`} />
            </animateMotion>
          </circle>

          {/* Floating label that follows the packet */}
          {label && (
            <g>
              <foreignObject
                width="200"
                height="60"
                x="-100"
                y="-40"
                style={{ overflow: 'visible' }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                  }}
                >
                  <div
                    style={{
                      padding: '6px 12px',
                      backgroundColor: 'rgba(15, 23, 42, 0.95)',
                      border: '1px solid rgba(34, 211, 238, 0.5)',
                      borderRadius: '8px',
                      color: '#22d3ee',
                      fontSize: '12px',
                      fontWeight: '600',
                      whiteSpace: 'nowrap',
                      boxShadow: '0 4px 6px rgba(0, 0, 0, 0.3)',
                      backdropFilter: 'blur(8px)',
                    }}
                  >
                    {label}
                  </div>
                </div>
                <animateMotion dur="2s" repeatCount="indefinite">
                  <mpath href={`#${id}`} />
                </animateMotion>
              </foreignObject>
            </g>
          )}
        </g>
      )}

      {/* Arrow marker */}
      <defs>
        <marker
          id={`arrow-${id}`}
          viewBox="0 0 10 10"
          refX="8"
          refY="5"
          markerWidth="8"
          markerHeight="8"
          orient="auto-start-reverse"
        >
          <path
            d="M 0 0 L 10 5 L 0 10 z"
            fill={animated ? '#22d3ee' : '#475569'}
            style={{
              transition: 'fill 0.3s ease',
            }}
          />
        </marker>
      </defs>
      <path
        d={edgePath}
        strokeWidth={3}
        stroke="transparent"
        fill="none"
        markerEnd={`url(#arrow-${id})`}
      />
    </>
  );
}

export default memo(AnimatedEdge);
