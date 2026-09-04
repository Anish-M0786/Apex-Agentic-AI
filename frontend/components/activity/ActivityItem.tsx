import type { Activity } from '@/types/activity';
import { ActivityIcon } from './ActivityIcon';

export function ActivityItem({ activity, index }: { activity: Activity; index: number }) {
  const state = activity.status === 'completed'
    ? 'Done'
    : activity.status === 'failed'
    ? 'Failed'
    : activity.status === 'running'
    ? 'Working'
    : 'Queued';

  return <li className={'activity-item ' + activity.status}>
    <span className="activity-step-marker">
      {activity.status === 'completed' ? '✓' : activity.status === 'failed' ? '!' : index + 1}
    </span>
    <ActivityIcon type={activity.type} />
    <span className="activity-label">{activity.label}</span>
    <small>{state}</small>
  </li>;
}
