import '@testing-library/jest-dom';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { CodeBlock } from './CodeBlock';

// Mock clipboard API
Object.assign(navigator, {
  clipboard: {
    writeText: vi.fn().mockResolvedValue(undefined),
  },
});

describe('CodeBlock', () => {
  it('renders the code and language', () => {
    render(<CodeBlock language="python" code="print('Hello World')" />);
    expect(screen.getByText('python')).toBeInTheDocument();
    expect(screen.getByText(/print/)).toBeInTheDocument();
  });

  it('copies code to clipboard', async () => {
    render(<CodeBlock language="python" code="print('Hello World')" />);
    const copyButton = screen.getByRole('button', { name: /Copy code/i });
    fireEvent.click(copyButton);

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("print('Hello World')");

    await waitFor(() => {
      expect(screen.getByText('Copied')).toBeInTheDocument();
    });
  });
});
