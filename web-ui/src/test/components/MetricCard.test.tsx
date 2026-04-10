import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MetricCard } from '../../components/MetricCard';

describe('MetricCard', () => {
  it('renders label and numeric value', () => {
    render(<MetricCard label="Devices" value={42} />);
    expect(screen.getByText('Devices')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
  });

  it('renders label and string value', () => {
    render(<MetricCard label="Status" value="OK" />);
    expect(screen.getByText('Status')).toBeInTheDocument();
    expect(screen.getByText('OK')).toBeInTheDocument();
  });

  it('renders sub text when provided', () => {
    render(<MetricCard label="Errors" value={5} sub="2.1% failure rate" />);
    expect(screen.getByText('2.1% failure rate')).toBeInTheDocument();
  });

  it('does not render sub text when omitted', () => {
    const { container } = render(<MetricCard label="Count" value={0} />);
    const subElements = container.querySelectorAll('.text-xs');
    expect(subElements.length).toBe(0);
  });
});
