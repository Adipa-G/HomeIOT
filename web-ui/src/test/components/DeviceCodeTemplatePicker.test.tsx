import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DeviceCodeTemplatePicker } from '../../components/DeviceCodeTemplatePicker';
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
    id: 'read-digital-pin',
    name: 'Read a digital pin',
    description: 'Read a button or switch.',
    setup_guide: 'Add a variable named value.',
    variants: [
      { platform: 'esp32', code: 'esp32 code here' },
      { platform: 'pico', code: 'pico code here' },
    ],
  },
];

describe('DeviceCodeTemplatePicker', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.setItem('auth_token', 'test-token');
  });

  it('does not fetch templates until opened', () => {
    renderWithProviders(
      <DeviceCodeTemplatePicker onSelect={vi.fn()}>
        {(open) => <button onClick={open}>Use a template</button>}
      </DeviceCodeTemplatePicker>,
    );

    expect(api.get).not.toHaveBeenCalled();
  });

  it('renders template list after opening', async () => {
    const user = userEvent.setup();
    vi.mocked(api.get).mockResolvedValue(templates);

    renderWithProviders(
      <DeviceCodeTemplatePicker onSelect={vi.fn()}>
        {(open) => <button onClick={open}>Use a template</button>}
      </DeviceCodeTemplatePicker>,
    );

    await user.click(screen.getByText('Use a template'));

    await waitFor(() => {
      expect(screen.getByText('Read a digital pin')).toBeInTheDocument();
    });
    expect(api.get).toHaveBeenCalledWith('/api/admin/modules/device-code-templates');
  });

  it('switching platform tabs changes the shown code', async () => {
    const user = userEvent.setup();
    vi.mocked(api.get).mockResolvedValue(templates);

    renderWithProviders(
      <DeviceCodeTemplatePicker onSelect={vi.fn()}>
        {(open) => <button onClick={open}>Use a template</button>}
      </DeviceCodeTemplatePicker>,
    );

    await user.click(screen.getByText('Use a template'));
    await waitFor(() => expect(screen.getByText('Read a digital pin')).toBeInTheDocument());
    await user.click(screen.getByText('Read a digital pin'));

    expect(screen.getByText('esp32 code here')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'pico' }));

    expect(screen.getByText('pico code here')).toBeInTheDocument();
  });

  it('clicking "Use this template" invokes onSelect with the active code and closes', async () => {
    const user = userEvent.setup();
    vi.mocked(api.get).mockResolvedValue(templates);
    const onSelect = vi.fn();

    renderWithProviders(
      <DeviceCodeTemplatePicker onSelect={onSelect}>
        {(open) => <button onClick={open}>Use a template</button>}
      </DeviceCodeTemplatePicker>,
    );

    await user.click(screen.getByText('Use a template'));
    await waitFor(() => expect(screen.getByText('Read a digital pin')).toBeInTheDocument());
    await user.click(screen.getByText('Read a digital pin'));
    await user.click(screen.getByRole('button', { name: 'Use this template' }));

    expect(onSelect).toHaveBeenCalledWith('esp32 code here');
    expect(screen.queryByText('Device Code Templates')).not.toBeInTheDocument();
  });
});
