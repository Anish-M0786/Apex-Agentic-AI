export type ActivityType = 'thinking' | 'planning' | 'plan_created' | 'step_started' | 'step_completed' | 'step_added' | 'tool_selection' | 'tool_execution' | 'retrieval' | 'generation' | 'artifact' | 'completion' | 'error';
export type ActivityStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
export interface Activity { id: string; type: ActivityType; status: ActivityStatus; label: string; tool?: string; step_id?: string; tool_label?: string; result_summary?: string; narration?: string; timestamp: string; metadata?: any; }
