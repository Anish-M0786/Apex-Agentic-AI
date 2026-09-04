'use client';

import { Check, X, Sparkles, ChevronDown, ChevronUp } from 'lucide-react';
import type { Activity, ActivityStatus } from '@/types/activity';
import { useMemo, useState } from 'react';

interface StepState {
  id: string;
  title: string;
  status: ActivityStatus;
  resultSummary?: string;
}

interface LiveActivityListProps {
  activities: Activity[];
  completed: boolean;
}

function StepIcon({ status }: { status: ActivityStatus }) {
  if (status === 'completed') {
    return (
      <span className="apex-step-icon apex-step-icon--done" aria-label="Completed">
        <Check size={11} strokeWidth={3} />
      </span>
    );
  }
  if (status === 'failed') {
    return (
      <span className="apex-step-icon apex-step-icon--failed" aria-label="Failed">
        <X size={11} strokeWidth={3} />
      </span>
    );
  }
  if (status === 'running') {
    return (
      <span className="apex-step-icon apex-step-icon--running" aria-label="Running">
        <span className="apex-orbit" aria-hidden="true" />
      </span>
    );
  }
  // pending / skipped
  return (
    <span className="apex-step-icon apex-step-icon--pending" aria-label="Pending">
      <span className="apex-dot" aria-hidden="true" />
    </span>
  );
}

export function LiveActivityList({ activities, completed }: LiveActivityListProps) {
  const [expanded, setExpanded] = useState(false);

  const { steps, isThinking } = useMemo(() => {
    const planEvent = activities.find((a) => a.type === 'plan_created');
    const planSteps: StepState[] = (planEvent?.metadata?.plan?.steps || []).map(
      (s: any) => ({
        id: s.id,
        title: s.title || s.tool || s.id,
        status: 'pending' as ActivityStatus,
      })
    );

    const map = new Map<string, StepState>(planSteps.map((s) => [s.id, { ...s }]));
    let isThinking = activities.some((a) => a.type === 'thinking' || a.type === 'planning');

    for (const ev of activities) {
      if (ev.type === 'plan_created') {
        isThinking = false;
        for (const s of ev.metadata?.plan?.steps || []) {
          if (!map.has(s.id)) {
            map.set(s.id, { id: s.id, title: s.title || s.tool || s.id, status: 'pending' });
          }
        }
      } else if (ev.type === 'step_added' && ev.metadata?.step) {
        const s = ev.metadata.step;
        map.set(s.id, { id: s.id, title: s.title, status: s.status || 'pending' });
      } else if (ev.type === 'step_started' && ev.step_id) {
        const existing = map.get(ev.step_id);
        if (existing) {
          existing.status = 'running';
          if (ev.tool_label) existing.title = ev.tool_label;
        } else {
          map.set(ev.step_id, {
            id: ev.step_id,
            title: ev.tool_label || ev.label,
            status: 'running',
          });
        }
      } else if (ev.type === 'step_completed' && ev.step_id) {
        const existing = map.get(ev.step_id);
        if (existing) {
          existing.status = 'completed';
          if (ev.result_summary) existing.resultSummary = ev.result_summary;
        }
      } else if (ev.type === 'error' && ev.step_id) {
        const existing = map.get(ev.step_id);
        if (existing) existing.status = 'failed';
      }
    }

    return { steps: Array.from(map.values()), isThinking };
  }, [activities]);

  if (!activities.length) return null;

  const hasFailed = steps.some((s) => s.status === 'failed');
  const completedCount = steps.filter((s) => s.status === 'completed').length;

  // Collapsed summary after completion
  if (completed && !expanded) {
    return (
      <div className="apex-activity-summary">
        <button
          onClick={() => setExpanded(true)}
          className="apex-activity-summary__btn"
          aria-label="Show task steps"
        >
          <span className={`apex-summary-icon ${hasFailed ? 'apex-summary-icon--fail' : 'apex-summary-icon--ok'}`}>
            {hasFailed ? <X size={12} strokeWidth={3} /> : <Check size={12} strokeWidth={3} />}
          </span>
          <span className="apex-summary-label">
            {hasFailed ? 'Partially completed' : 'Completed'}
          </span>
          <span className="apex-summary-count">· {steps.length} steps</span>
          <ChevronDown size={14} className="apex-summary-chevron" />
        </button>
      </div>
    );
  }

  return (
    <div className="apex-activity" role="status" aria-live="polite" aria-label="Task progress">
      {/* Header */}
      <div className="apex-activity__header">
        <span className={`apex-header-spark ${!completed ? 'apex-header-spark--active' : ''}`} aria-hidden="true">
          <Sparkles size={13} />
        </span>
        <span className="apex-activity__header-label">
          {completed ? (hasFailed ? 'Partially completed' : 'Completed') : 'Working'}
        </span>

        {completed && (
          <button
            onClick={() => setExpanded(false)}
            className="apex-collapse-btn"
            aria-label="Collapse steps"
          >
            <ChevronUp size={14} />
          </button>
        )}
      </div>

      {/* Steps */}
      <ol className="apex-steps" aria-label="Steps">
        {isThinking && steps.length === 0 && (
          <li className="apex-step apex-step--running">
            <StepIcon status="running" />
            <span className="apex-step__title">Understanding request</span>
          </li>
        )}

        {steps.map((step) => (
          <li
            key={step.id}
            className={`apex-step apex-step--${step.status}`}
          >
            <StepIcon status={step.status} />
            <span className="apex-step__body">
              <span className="apex-step__title">{step.title}</span>
              {step.resultSummary && (
                <span className="apex-step__meta">{step.resultSummary}</span>
              )}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}
