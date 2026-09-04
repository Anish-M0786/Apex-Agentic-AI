import '@testing-library/jest-dom/vitest';
import { render, screen } from '@testing-library/react';
import { ThinkingIndicator } from './ThinkingIndicator';
import { ArtifactCard } from '@/components/artifacts/ArtifactCard';
import { describe, expect, it } from 'vitest';
describe('activity UI', () => {
  it('announces safe thinking status', () => { render(<ThinkingIndicator/>); expect(screen.getByRole('status')).toHaveTextContent('Thinking'); });
  it('renders artifact download link', () => { render(<ArtifactCard artifact={{filename:'notes.pdf',type:'pdf',url:'/api/files/notes.pdf'}}/>); expect(screen.getByLabelText('Download notes.pdf')).toBeTruthy(); });
});
