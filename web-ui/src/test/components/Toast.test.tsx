import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { ToastContainer, toast } from '../../components/Toast';

describe('ToastContainer', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders nothing initially', () => {
    const { container } = render(<ToastContainer />);
    expect(container.querySelectorAll('.shadow-md').length).toBe(0);
  });

  it('shows a success toast', () => {
    render(<ToastContainer />);
    act(() => { toast('Saved!'); });
    expect(screen.getByText('Saved!')).toBeInTheDocument();
    expect(screen.getByText('Saved!').className).toContain('bg-green-600');
  });

  it('shows an error toast', () => {
    render(<ToastContainer />);
    act(() => { toast('Failed!', 'error'); });
    expect(screen.getByText('Failed!')).toBeInTheDocument();
    expect(screen.getByText('Failed!').className).toContain('bg-red-600');
  });

  it('removes toast after timeout', () => {
    vi.useFakeTimers();
    render(<ToastContainer />);
    act(() => { toast('Temporary'); });
    expect(screen.getByText('Temporary')).toBeInTheDocument();

    act(() => { vi.advanceTimersByTime(3500); });
    expect(screen.queryByText('Temporary')).not.toBeInTheDocument();
  });

  it('shows multiple toasts', () => {
    render(<ToastContainer />);
    act(() => {
      toast('First');
      toast('Second', 'error');
    });
    expect(screen.getByText('First')).toBeInTheDocument();
    expect(screen.getByText('Second')).toBeInTheDocument();
  });
});
