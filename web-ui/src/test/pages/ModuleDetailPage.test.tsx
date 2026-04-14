import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ModuleDetailPage from '../../pages/ModuleDetailPage';
import { renderWithProviders } from '../test-utils';
import { api } from '../../api/client';

vi.mock('../../api/client', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    upload: vi.fn(),
  },
  ApiError: class ApiError extends Error {
    error: { message: string };
    constructor(msg: string) { super(msg); this.error = { message: msg }; }
  },
}));

vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router');
  return { ...actual, useParams: () => ({ moduleId: 'sensor-reader' }), useNavigate: () => vi.fn() };
});

const mockModule = {
  module_id: 'sensor-reader',
  description: 'Reads DHT22 sensors',
  default_entrypoint: 'run',
  created_at_utc: '2026-05-10T00:00:00Z',
  updated_at_utc: '2026-05-10T00:00:00Z',
  versions: [
    { id: 'v1', version: '1.0.0', package_hash: 'sha256:abc123def456', package_size_bytes: 256, created_at_utc: '2026-05-10T00:00:00Z' },
  ],
  assignments: [
    { id: 'a1', device_id: 'esp32-001', module_id: 'sensor-reader', version: '1.0.0', interval_ms: 60000, timeout_ms: 30000, entrypoint: 'run', enabled: true, created_at_utc: '2026-05-10T00:00:00Z', updated_at_utc: '2026-05-10T00:00:00Z' },
  ],
};

describe('ModuleDetailPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.setItem('auth_token', 'test-token');
  });

  it('renders module detail with versions and assignments', async () => {
    vi.mocked(api.get).mockResolvedValue(mockModule);
    renderWithProviders(<ModuleDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('Versions')).toBeInTheDocument();
    });
    expect(screen.getByText('Reads DHT22 sensors')).toBeInTheDocument();
    expect(screen.getAllByText('1.0.0').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('esp32-001')).toBeInTheDocument();
  });

  it('shows File and Code upload mode toggles', async () => {
    vi.mocked(api.get).mockResolvedValue(mockModule);
    renderWithProviders(<ModuleDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('Versions')).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: 'File' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Code' })).toBeInTheDocument();
  });

  it('switches to code mode and shows textarea', async () => {
    const user = userEvent.setup();
    vi.mocked(api.get).mockResolvedValue(mockModule);
    renderWithProviders(<ModuleDetailPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Code' })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: 'Code' }));
    expect(screen.getByPlaceholderText(/def run/)).toBeInTheDocument();
    expect(screen.getByText('Save Version')).toBeInTheDocument();
  });

  it('shows View button for versions to see code', async () => {
    vi.mocked(api.get).mockResolvedValue(mockModule);
    renderWithProviders(<ModuleDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('View')).toBeInTheDocument();
    });
  });

  it('fetches and displays code when View is clicked', async () => {
    const user = userEvent.setup();
    vi.mocked(api.get)
      .mockResolvedValueOnce(mockModule)
      .mockResolvedValueOnce({ code: 'def run(ctx):\n    return True' });

    renderWithProviders(<ModuleDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('View')).toBeInTheDocument();
    });

    await user.click(screen.getByText('View'));

    await waitFor(() => {
      expect(screen.getByText(/def run\(ctx\)/)).toBeInTheDocument();
    });
  });
});
