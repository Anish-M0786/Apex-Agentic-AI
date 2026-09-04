import { Sparkles, FileText, Code, Presentation, MessageSquare } from 'lucide-react';

const quickActions = [
  { label: 'Create a presentation', icon: Presentation, query: 'Create a presentation on ' },
  { label: 'Analyze a document', icon: FileText, query: 'Analyze the attached document and ' },
  { label: 'Write code', icon: Code, query: 'Write a React component that ' },
  { label: 'Brainstorm ideas', icon: MessageSquare, query: 'Let\'s brainstorm ideas for ' },
];

export function WelcomeScreen({ onSelect }: { onSelect: (text: string) => void }) { 
  return (
    <section className="welcome-premium">
      <div className="welcome-header">
        <span className="welcome-eyebrow"><Sparkles size={16} /> LOCAL AI WORKSPACE</span>
        <h1 className="welcome-title">Welcome to Apex</h1>
        <p className="welcome-subtitle">Your intelligent workspace for documents, code, and creation. How can I help you today?</p>
      </div>
      <div className="quick-actions-grid">
        {quickActions.map(action => (
          <button key={action.label} className="quick-action-card" onClick={() => onSelect(action.query)}>
            <action.icon size={24} className="quick-action-icon" />
            <span className="quick-action-label">{action.label}</span>
          </button>
        ))}
      </div>
    </section>
  ); 
}
