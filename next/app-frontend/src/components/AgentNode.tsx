import { memo } from 'react';
import { Handle, Position } from 'reactflow';
import type { NodeProps } from 'reactflow';
import type { AgentNodeData } from '../types/relay';

function AgentNode({ data }: NodeProps<AgentNodeData>) {
  return (
    <div
      className={`
        relative px-6 py-5 rounded-2xl border-2 shadow-2xl transition-all duration-500
        min-w-[320px] max-w-[380px] backdrop-blur-sm
        ${
          data.active
            ? 'border-cyan-400 bg-gradient-to-br from-slate-800/95 to-slate-900/95 shadow-cyan-500/30 scale-105'
            : 'border-slate-700 bg-gradient-to-br from-slate-800/90 to-slate-900/90 hover:border-slate-600'
        }
      `}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!bg-slate-600 !w-3 !h-3 !border-2 !border-slate-800"
      />

      <div className="space-y-3">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            <h3 className="text-lg font-bold text-white mb-1">{data.label}</h3>
            <p className="text-xs text-slate-400">{data.subtitle}</p>
          </div>
          {data.active && (
            <div className="flex items-center gap-1.5 ml-2">
              <div className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-pulse" />
              <div className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-pulse [animation-delay:0.2s]" />
              <div className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-pulse [animation-delay:0.4s]" />
            </div>
          )}
        </div>

        {/* Input Section */}
        {data.inputData && (
          <div className="border-t border-slate-700/50 pt-3">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs font-semibold text-slate-400">📥 INPUT</span>
            </div>
            <div className="p-3 bg-slate-900/70 rounded-lg border border-slate-700/50 max-h-24 overflow-y-auto">
              <p className="text-xs text-slate-300 leading-relaxed">
                {typeof data.inputData === 'string'
                  ? data.inputData.substring(0, 200) + (data.inputData.length > 200 ? '...' : '')
                  : JSON.stringify(data.inputData).substring(0, 150) + '...'}
              </p>
            </div>
          </div>
        )}

        {/* Active processing indicator */}
        {data.active && (
          <div className="flex items-center gap-2 py-2">
            <div className="flex-1 h-1 bg-slate-700 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-cyan-400 to-blue-500 animate-pulse" />
            </div>
            <span className="text-xs text-cyan-400 font-medium whitespace-nowrap">
              Processing
            </span>
          </div>
        )}

        {/* Output Section */}
        {data.outputData && (
          <div className="border-t border-slate-700/50 pt-3">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs font-semibold text-emerald-400">📤 OUTPUT</span>
            </div>
            <div className="p-3 bg-emerald-500/5 rounded-lg border border-emerald-500/20 max-h-32 overflow-y-auto">
              {renderOutput(data.outputData)}
            </div>
          </div>
        )}
      </div>

      <Handle
        type="source"
        position={Position.Right}
        className="!bg-slate-600 !w-3 !h-3 !border-2 !border-slate-800"
      />
    </div>
  );
}

function renderOutput(outputData: any) {
  if (!outputData) return null;

  // Analyzer output
  if (outputData.summary || outputData.strengths || outputData.gaps) {
    return (
      <div className="space-y-2 text-xs text-slate-300">
        {outputData.summary && (
          <div>
            <span className="font-semibold text-slate-400">Summary:</span>
            <p className="mt-1">{outputData.summary}</p>
          </div>
        )}
        {outputData.strengths && (
          <div>
            <span className="font-semibold text-emerald-400">✓ Strengths:</span>
            <ul className="mt-1 ml-4 space-y-1">
              {outputData.strengths.map((s: string, i: number) => (
                <li key={i} className="list-disc">{s}</li>
              ))}
            </ul>
          </div>
        )}
        {outputData.gaps && (
          <div>
            <span className="font-semibold text-amber-400">! Gaps:</span>
            <ul className="mt-1 ml-4 space-y-1">
              {outputData.gaps.map((g: string, i: number) => (
                <li key={i} className="list-disc">{g}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  }

  // Designer output
  if (outputData.interviewQuestions || outputData.rationale) {
    return (
      <div className="space-y-2 text-xs text-slate-300">
        {outputData.interviewQuestions && (
          <div>
            <span className="font-semibold text-emerald-400">❓ {outputData.interviewQuestions.length} Questions:</span>
            <ol className="mt-1 ml-4 space-y-1">
              {outputData.interviewQuestions.map((q: string, i: number) => (
                <li key={i} className="list-decimal">{q}</li>
              ))}
            </ol>
          </div>
        )}
        {outputData.rationale && (
          <div className="mt-2">
            <span className="font-semibold text-slate-400">Rationale:</span>
            <p className="mt-1 text-slate-400">{outputData.rationale}</p>
          </div>
        )}
      </div>
    );
  }

  // Evaluator output
  if (outputData.score !== undefined || outputData.notes) {
    return (
      <div className="space-y-2 text-xs text-slate-300">
        {outputData.score !== undefined && (
          <div className="flex items-center gap-2">
            <span className="font-semibold text-emerald-400">⭐ Score:</span>
            <span className="text-lg font-bold text-emerald-300">{outputData.score}/10</span>
          </div>
        )}
        {outputData.notes && (
          <div>
            <span className="font-semibold text-slate-400">Notes:</span>
            <p className="mt-1 text-slate-400">{outputData.notes}</p>
          </div>
        )}
      </div>
    );
  }

  // Fallback for unknown output
  return (
    <p className="text-xs text-slate-300 line-clamp-3">
      {JSON.stringify(outputData, null, 2)}
    </p>
  );
}

export default memo(AgentNode);
