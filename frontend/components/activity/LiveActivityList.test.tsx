import '@testing-library/jest-dom/vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { LiveActivityList } from './LiveActivityList';
import { describe, expect, it } from 'vitest';
import { Activity } from '@/types/activity';

const mockActivities: Activity[] = [
  {
    id: 'e1',
    type: 'plan_created',
    status: 'completed',
    label: 'Plan',
    timestamp: '2026-01-01',
    metadata: {
      plan: {
        steps: [
          { id: 's1', tool: 'analyze', title: 'Analyze topic' },
          { id: 's2', tool: 'generate', title: 'Generate content' }
        ]
      }
    }
  },
  {
    id: 'e2',
    type: 'step_started',
    step_id: 's1',
    status: 'running',
    label: 'Analyze',
    tool_label: 'Analyze topic',
    timestamp: '2026-01-01'
  }
];

describe('LiveActivityList', () => {
  it('renders nothing when there are no activities', () => {
    const { container } = render(<LiveActivityList activities={[]} completed={false} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders the active steps based on plan_created and step_started events', () => {
    render(<LiveActivityList activities={mockActivities} completed={false} />);
    expect(screen.getByText('Working')).toBeInTheDocument();
    expect(screen.getByText('Analyze topic')).toBeInTheDocument();
    expect(screen.getByText('Generate content')).toBeInTheDocument();
  });

  it('collapses into a summary when completed', () => {
    const completedActivities: Activity[] = [
      ...mockActivities,
      { id: 'e3', type: 'step_completed', step_id: 's1', status: 'completed', label: 'Done', timestamp: '2026-01-01' },
      { id: 'e4', type: 'step_completed', step_id: 's2', status: 'completed', label: 'Done', timestamp: '2026-01-01' },
    ];
    render(<LiveActivityList activities={completedActivities} completed={true} />);
    expect(screen.getByRole('button')).toHaveTextContent('Completed · 2 steps');
    expect(screen.queryByText('Working')).not.toBeInTheDocument();
  });

  it('allows expanding and collapsing when completed', () => {
    const completedActivities: Activity[] = [
      ...mockActivities,
      { id: 'e3', type: 'step_completed', step_id: 's1', status: 'completed', label: 'Done', timestamp: '2026-01-01' },
    ];
    render(<LiveActivityList activities={completedActivities} completed={true} />);
    
    // Expand
    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByText('Working')).toBeInTheDocument();
    expect(screen.getByText('Analyze topic')).toBeInTheDocument();
    
    // Collapse
    fireEvent.click(screen.getByText('Collapse'));
    expect(screen.getByRole('button')).toHaveTextContent('Completed · 2 steps');
  });

  it('handles dynamically added steps', () => {
    const activitiesWithAddedStep: Activity[] = [
      ...mockActivities,
      {
        id: 'e3',
        type: 'step_added',
        status: 'pending',
        label: 'Added',
        timestamp: '2026-01-01',
        metadata: {
          step: { id: 's3', title: 'Generate visual assets', status: 'pending' }
        }
      }
    ];
    render(<LiveActivityList activities={activitiesWithAddedStep} completed={false} />);
    expect(screen.getByText('Generate visual assets')).toBeInTheDocument();
  });
});
