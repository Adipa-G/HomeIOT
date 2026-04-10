import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import ModulesPage from '../../pages/ModulesPage';
import { renderWithProviders } from '../test-utils';
import { api } from '../../api/client';

vi.mock('../../api/client', () => ({
  api: {
    get: vi.fn(),
  },
}));

const mockModules = [
  {
    module_id: 'mod-temp-sensor',
    name: 'Temperature Sensor',
    platform: 'esp32',
    description: 'Reads DHT22',
    default_entrypoint: 'main.py',
    version_count: 3,
    assignment_count: 2,
    created_at_utc: '2026-05-10T00:00:00Z',
  },
  {
    module_id: 'mod-led-blink',
    name: 'LED Blink',
    platform: 'pico',
    description: null,
    default_entrypoint: 'main.py',
    version_count: 1,
    assignment_count: 0,
    created_at_utc: '2026-05-20T00:00:00Z',
  },
];

describe('ModulesPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.setItem('auth_token', 'test-token');
  });

  it('shows loading state', () => {
    vi.mocked(api.get).mockReturnValue(new Promise(() => {}));
    renderWithProviders(<ModulesPage />);
    expect(screen.getByText('Loading…')).toBeInTheDocument();
  });

  it('renders module list', async () => {
    vi.mocked(api.get).mockResolvedValue(mockModules);
    renderWithProviders(<ModulesPage />);

    await waitFor(() => {
      expect(screen.getByText('Temperature Sensor')).toBeInTheDocument();
    });
    expect(screen.getByText('LED Blink')).toBeInTheDocument();
    expect(screen.getByText('mod-temp-sensor')).toBeInTheDocument();
  });

  it('shows "No modules found" when empty', async () => {
    vi.mocked(api.get).mockResolvedValue([]);
    renderWithProviders(<ModulesPage />);

    await waitFor(() => {
      expect(screen.getByText('No modules found.')).toBeInTheDocument();
    });
  });

  it('has a Create Module link', () => {
    vi.mocked(api.get).mockReturnValue(new Promise(() => {}));
    renderWithProviders(<ModulesPage />);
    expect(screen.getByText('Create Module')).toBeInTheDocument();
  });
});
