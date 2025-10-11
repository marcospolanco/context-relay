import { useState } from 'react';
import { sendInitialize, sendRelay } from '../lib/relayClient';

export default function DemoControls() {
  const [input, setInput] = useState(
    'Senior Software Engineer with 5 years of experience in backend development, team leadership, and microservices architecture.'
  );
  const [contextId, setContextId] = useState<string>('');
  const [currentStep, setCurrentStep] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleStart = async () => {
    if (!input.trim()) return;

    setIsProcessing(true);
    try {
      const result = await sendInitialize(input);
      setContextId(result.contextId);
      setCurrentStep(1);
    } catch (err) {
      console.error('Failed to initialize:', err);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleStep = async (from: string, to: string, stepNum: number) => {
    if (!contextId) return;

    setIsProcessing(true);
    try {
      await sendRelay({
        from,
        to,
        contextId,
      });
      setCurrentStep(stepNum);
    } catch (err) {
      console.error('Failed to relay:', err);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReset = () => {
    setContextId('');
    setCurrentStep(0);
    setInput(
      'Senior Software Engineer with 5 years of experience in backend development, team leadership, and microservices architecture.'
    );
    // Dispatch event to clear the flow visualization
    window.dispatchEvent(new Event('resetFlow'));
  };

  const handleRunAll = async () => {
    if (!input.trim()) return;

    setIsProcessing(true);
    try {
      // Step 1: Initialize
      const result = await sendInitialize(input);
      setContextId(result.contextId);
      setCurrentStep(1);

      // Wait a bit for visualization
      await new Promise((resolve) => setTimeout(resolve, 1500));

      // Step 2: Analyzer -> Designer
      await sendRelay({
        from: 'analyzer',
        to: 'designer',
        contextId: result.contextId,
      });
      setCurrentStep(2);

      await new Promise((resolve) => setTimeout(resolve, 1500));

      // Step 3: Designer -> Evaluator
      await sendRelay({
        from: 'designer',
        to: 'evaluator',
        contextId: result.contextId,
      });
      setCurrentStep(3);
    } catch (err) {
      console.error('Failed to run flow:', err);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="absolute top-6 left-6 z-10 backdrop-blur-xl bg-slate-800/90 rounded-2xl shadow-2xl border border-slate-700/50 p-6 w-[420px]">
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-lg font-semibold text-white">Context Relay</h3>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isProcessing ? 'bg-emerald-400 animate-pulse' : 'bg-slate-600'}`} />
          <span className="text-xs text-slate-400">{isProcessing ? 'Active' : 'Ready'}</span>
        </div>
      </div>

      <div className="space-y-4">
        {/* Input field */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Resume Input
          </label>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={currentStep > 0}
            className="w-full px-4 py-3 bg-slate-900/80 border border-slate-700 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed resize-none"
            rows={3}
            placeholder="Enter resume or candidate description..."
          />
        </div>

        {/* Progress indicators */}
        {currentStep > 0 && (
          <div className="flex items-center gap-2 py-3">
            <StepDot active={currentStep >= 1} label="A" />
            <ProgressLine active={currentStep >= 2} />
            <StepDot active={currentStep >= 2} label="D" />
            <ProgressLine active={currentStep >= 3} />
            <StepDot active={currentStep >= 3} label="E" />
          </div>
        )}

        {/* Control buttons */}
        <div className="space-y-2">
          {currentStep === 0 && (
            <>
              <button
                onClick={handleRunAll}
                disabled={isProcessing || !input.trim()}
                className="w-full px-5 py-3 bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-400 hover:to-blue-400 text-white rounded-lg font-medium text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/30"
              >
                {isProcessing ? 'Processing...' : 'Run Full Flow'}
              </button>
              <button
                onClick={handleStart}
                disabled={isProcessing || !input.trim()}
                className="w-full px-5 py-3 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg font-medium text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Step by Step
              </button>
            </>
          )}

          {currentStep === 1 && (
            <button
              onClick={() => handleStep('analyzer', 'designer', 2)}
              disabled={isProcessing}
              className="w-full px-5 py-3 bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-400 hover:to-blue-400 text-white rounded-lg font-medium text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-cyan-500/20"
            >
              {isProcessing ? 'Processing...' : 'Send to Designer →'}
            </button>
          )}

          {currentStep === 2 && (
            <button
              onClick={() => handleStep('designer', 'evaluator', 3)}
              disabled={isProcessing}
              className="w-full px-5 py-3 bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-400 hover:to-blue-400 text-white rounded-lg font-medium text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-cyan-500/20"
            >
              {isProcessing ? 'Processing...' : 'Send to Evaluator →'}
            </button>
          )}

          {currentStep >= 1 && (
            <button
              onClick={handleReset}
              disabled={isProcessing}
              className="w-full px-5 py-3 bg-slate-700/50 hover:bg-slate-700 text-slate-300 rounded-lg font-medium text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed border border-slate-600"
            >
              Reset
            </button>
          )}
        </div>

        {currentStep === 3 && (
          <div className="mt-3 p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
            <p className="text-sm text-emerald-400 font-medium flex items-center gap-2">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Flow completed successfully!
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function StepDot({ active, label }: { active: boolean; label: string }) {
  return (
    <div
      className={`w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
        active
          ? 'bg-gradient-to-br from-cyan-400 to-blue-500 text-white shadow-lg shadow-cyan-500/30'
          : 'bg-slate-700 text-slate-500'
      }`}
    >
      {label}
    </div>
  );
}

function ProgressLine({ active }: { active: boolean }) {
  return (
    <div className="flex-1 h-0.5 bg-slate-700 rounded-full overflow-hidden">
      {active && <div className="h-full bg-gradient-to-r from-cyan-400 to-blue-500" />}
    </div>
  );
}
