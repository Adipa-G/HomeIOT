import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatusBadge } from '../../components/StatusBadge';

describe('StatusBadge', () => {
  it('renders the text', () => {
    render(<StatusBadge text="active" />);
    expect(screen.getByText('active')).toBeInTheDocument();
  });

  it('defaults to gray variant', () => {
    render(<StatusBadge text="unknown" />);
    const badge = screen.getByText('unknown');
    expect(badge.className).toContain('bg-gray-100');
  });

  it('applies green variant classes', () => {
    render(<StatusBadge text="online" variant="green" />);
    const badge = screen.getByText('online');
    expect(badge.className).toContain('bg-green-100');
    expect(badge.className).toContain('text-green-800');
  });

  it('applies red variant classes', () => {
    render(<StatusBadge text="error" variant="red" />);
    const badge = screen.getByText('error');
    expect(badge.className).toContain('bg-red-100');
  });

  it('applies yellow variant classes', () => {
    render(<StatusBadge text="pending" variant="yellow" />);
    const badge = screen.getByText('pending');
    expect(badge.className).toContain('bg-yellow-100');
  });
});
