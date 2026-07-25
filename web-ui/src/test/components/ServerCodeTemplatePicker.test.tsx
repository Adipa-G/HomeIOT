import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ServerCodeTemplatePicker } from '../../components/ServerCodeTemplatePicker';
import { renderWithProviders } from '../test-utils';
import { api } from '../../api/client';

vi.mock('../../api/client', () => ({
  api: { get: vi.fn() },
  ApiError: class ApiError extends Error {
    error: { message: string };
    constructor(msg: string) { super(msg); this.error = { message: msg }; }
  },
}));

const templates = [
  {
    id: 'static-value',
    name: 'Static value',
    description: 'Return a fixed value.',
    setup_guide: 'Paste into Server Code.',
    code: 'return 28;',
  },
];

describe('ServerCodeTemplatePicker', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.setItem('auth_token', 'test-token');
  });

  it('does not fetch templates until opened', () => {
    renderWithProviders(
      <ServerCodeTemplatePicker onSelect={vi.fn()}>
        {(open) => <button onClick={open}>Use a template</button>}
      </ServerCodeTemplatePicker>,
    );

    expect(api.get).not.toHaveBeenCalled();
  });

  it('renders template list after opening', async () => {
    const user = userEvent.setup();
    vi.mocked(api.get).mockResolvedValue(templates);

    renderWithProviders(
      <ServerCodeTemplatePicker onSelect={vi.fn()}>
        {(open) => <button onClick={open}>Use a template</button>}
      </ServerCodeTemplatePicker>,
    );

    await user.click(screen.getByText('Use a template'));

    await waitFor(() => {
      expect(screen.getByText('Static value')).toBeInTheDocument();
    });
    expect(api.get).toHaveBeenCalledWith('/api/admin/modules/server-code-templates');
  });

  it('selecting a template shows its code and setup guide', async () => {
    const user = userEvent.setup();
    vi.mocked(api.get).mockResolvedValue(templates);

    renderWithProviders(
      <ServerCodeTemplatePicker onSelect={vi.fn()}>
        {(open) => <button onClick={open}>Use a template</button>}
      </ServerCodeTemplatePicker>,
    );

    await user.click(screen.getByText('Use a template'));
    await waitFor(() => expect(screen.getByText('Static value')).toBeInTheDocument());
    await user.click(screen.getByText('Static value'));

    expect(screen.getByText('return 28;')).toBeInTheDocument();
    expect(screen.getByText('Paste into Server Code.')).toBeInTheDocument();
  });

  it('clicking "Use this template" invokes onSelect with the code and closes', async () => {
    const user = userEvent.setup();
    vi.mocked(api.get).mockResolvedValue(templates);
    const onSelect = vi.fn();

    renderWithProviders(
      <ServerCodeTemplatePicker onSelect={onSelect}>
        {(open) => <button onClick={open}>Use a template</button>}
      </ServerCodeTemplatePicker>,
    );

    await user.click(screen.getByText('Use a template'));
    await waitFor(() => expect(screen.getByText('Static value')).toBeInTheDocument());
    await user.click(screen.getByText('Static value'));
    await user.click(screen.getByRole('button', { name: 'Use this template' }));

    expect(onSelect).toHaveBeenCalledWith('return 28;');
    expect(screen.queryByText('Server Code Templates')).not.toBeInTheDocument();
  });
});
