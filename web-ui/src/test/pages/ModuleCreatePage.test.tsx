import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ModuleCreatePage from '../../pages/ModuleCreatePage';
import { renderWithProviders } from '../test-utils';
import { api } from '../../api/client';

vi.mock('../../api/client', () => ({
  api: { post: vi.fn(), get: vi.fn() },
  ApiError: class ApiError extends Error {
    error: { message: string };
    constructor(msg: string) { super(msg); this.error = { message: msg }; }
  },
}));

describe('ModuleCreatePage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.setItem('auth_token', 'test-token');
  });

  it('renders form with Module ID, Description, Version, and Code fields', () => {
    renderWithProviders(<ModuleCreatePage />);
    expect(screen.getByRole('heading', { name: 'Create Module' })).toBeInTheDocument();
    expect(screen.getByText('Module ID')).toBeInTheDocument();
    expect(screen.getByText('Description')).toBeInTheDocument();
    expect(screen.getByText(/Version/)).toBeInTheDocument();
    expect(screen.getByText(/Code/)).toBeInTheDocument();
  });

  it('submits form with module_id and description', async () => {
    const user = userEvent.setup();
    vi.mocked(api.post).mockResolvedValue({ module_id: 'test-mod' });
    renderWithProviders(<ModuleCreatePage />);

    await user.type(screen.getByPlaceholderText('e.g. sensor-reader'), 'test-mod');
    await user.click(screen.getByRole('button', { name: /create module/i }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/api/admin/modules', expect.objectContaining({
        module_id: 'test-mod',
      }));
    });
  });

  it('shows version warning when code is entered without version', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ModuleCreatePage />);

    const codeTextarea = screen.getByPlaceholderText(/def run/);
    await user.type(codeTextarea, 'def run(ctx): pass');

    expect(screen.getByText(/Version is required when code is provided/)).toBeInTheDocument();
  });

  it('opens the template picker and inserts selected template code and version', async () => {
    const user = userEvent.setup();
    const templates = [
      {
        id: 'read-digital-pin',
        name: 'Read a digital pin',
        description: 'Read a button or switch.',
        setup_guide: 'Add a variable named value.',
        variants: [
          { platform: 'esp32', code: 'from machine import Pin\n' },
        ],
      },
    ];
    vi.mocked(api.get).mockResolvedValue(templates);

    renderWithProviders(<ModuleCreatePage />);

    await user.click(screen.getByRole('button', { name: 'Use a template' }));

    await waitFor(() => {
      expect(screen.getByText('Read a digital pin')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Read a digital pin'));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Use this template' })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: 'Use this template' }));

    expect(screen.getByDisplayValue(/from machine import Pin/)).toBeInTheDocument();
    expect(screen.getByDisplayValue('1.0.0')).toBeInTheDocument();
  });
});
