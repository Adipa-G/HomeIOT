import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfirmModal } from '../../components/ConfirmModal';

describe('ConfirmModal', () => {
  it('does not show modal by default', () => {
    render(
      <ConfirmModal title="Delete?" onConfirm={vi.fn()}>
        {(open) => <button onClick={open}>Open</button>}
      </ConfirmModal>,
    );
    expect(screen.queryByText('Delete?')).not.toBeInTheDocument();
  });

  it('shows modal when trigger is clicked', async () => {
    const user = userEvent.setup();
    render(
      <ConfirmModal title="Delete item?" description="This cannot be undone." onConfirm={vi.fn()}>
        {(open) => <button onClick={open}>Open</button>}
      </ConfirmModal>,
    );
    await user.click(screen.getByText('Open'));
    expect(screen.getByText('Delete item?')).toBeInTheDocument();
    expect(screen.getByText('This cannot be undone.')).toBeInTheDocument();
  });

  it('closes modal on Cancel click', async () => {
    const user = userEvent.setup();
    render(
      <ConfirmModal title="Delete?" onConfirm={vi.fn()}>
        {(open) => <button onClick={open}>Open</button>}
      </ConfirmModal>,
    );
    await user.click(screen.getByText('Open'));
    expect(screen.getByText('Delete?')).toBeInTheDocument();
    await user.click(screen.getByText('Cancel'));
    expect(screen.queryByText('Delete?')).not.toBeInTheDocument();
  });

  it('calls onConfirm and closes on confirm click', async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn().mockResolvedValue(undefined);
    render(
      <ConfirmModal title="Delete?" onConfirm={onConfirm}>
        {(open) => <button onClick={open}>Open</button>}
      </ConfirmModal>,
    );
    await user.click(screen.getByText('Open'));
    await user.click(screen.getByText('Delete'));
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it('uses custom confirm label', async () => {
    const user = userEvent.setup();
    render(
      <ConfirmModal title="Remove?" confirmLabel="Remove" onConfirm={vi.fn()}>
        {(open) => <button onClick={open}>Open</button>}
      </ConfirmModal>,
    );
    await user.click(screen.getByText('Open'));
    expect(screen.getByText('Remove')).toBeInTheDocument();
  });
});
