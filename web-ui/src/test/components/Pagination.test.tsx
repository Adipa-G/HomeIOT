import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Pagination } from '../../components/Pagination';

describe('Pagination', () => {
  it('shows "No results" when total is 0', () => {
    render(<Pagination offset={0} limit={25} total={0} onChange={vi.fn()} />);
    expect(screen.getByText('No results')).toBeInTheDocument();
  });

  it('shows range text', () => {
    render(<Pagination offset={0} limit={25} total={100} onChange={vi.fn()} />);
    expect(screen.getByText('1–25 of 100')).toBeInTheDocument();
  });

  it('shows correct range on second page', () => {
    render(<Pagination offset={25} limit={25} total={100} onChange={vi.fn()} />);
    expect(screen.getByText('26–50 of 100')).toBeInTheDocument();
  });

  it('clamps end to total on last page', () => {
    render(<Pagination offset={75} limit={25} total={90} onChange={vi.fn()} />);
    expect(screen.getByText('76–90 of 90')).toBeInTheDocument();
  });

  it('disables Prev on first page', () => {
    render(<Pagination offset={0} limit={25} total={100} onChange={vi.fn()} />);
    expect(screen.getByText('Prev')).toBeDisabled();
  });

  it('disables Next on last page', () => {
    render(<Pagination offset={75} limit={25} total={100} onChange={vi.fn()} />);
    expect(screen.getByText('Next')).toBeDisabled();
  });

  it('calls onChange with next offset on Next click', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<Pagination offset={0} limit={25} total={100} onChange={onChange} />);
    await user.click(screen.getByText('Next'));
    expect(onChange).toHaveBeenCalledWith(25);
  });

  it('calls onChange with previous offset on Prev click', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<Pagination offset={25} limit={25} total={100} onChange={onChange} />);
    await user.click(screen.getByText('Prev'));
    expect(onChange).toHaveBeenCalledWith(0);
  });
});
