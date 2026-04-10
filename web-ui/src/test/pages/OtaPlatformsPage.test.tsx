import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import OtaPlatformsPage from '../../pages/OtaPlatformsPage';
import { renderWithProviders } from '../test-utils';
import { api } from '../../api/client';

vi.mock('../../api/client', () => ({
  api: {
    get: vi.fn(),
  },
}));

describe('OtaPlatformsPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.setItem('auth_token', 'test-token');
  });

  it('shows loading state', () => {
    vi.mocked(api.get).mockReturnValue(new Promise(() => {}));
    renderWithProviders(<OtaPlatformsPage />);
    expect(screen.getByText('Loading…')).toBeInTheDocument();
  });

  it('renders platform cards', async () => {
    vi.mocked(api.get).mockResolvedValue([
      { platform: 'esp32', release_count: 3 },
      { platform: 'pico', release_count: 1 },
    ]);
    renderWithProviders(<OtaPlatformsPage />);

    await waitFor(() => {
      expect(screen.getByText('esp32')).toBeInTheDocument();
    });
    expect(screen.getByText('pico')).toBeInTheDocument();
    expect(screen.getByText('3 releases')).toBeInTheDocument();
    expect(screen.getByText('1 release')).toBeInTheDocument();
  });

  it('shows "No platforms found" when empty', async () => {
    vi.mocked(api.get).mockResolvedValue([]);
    renderWithProviders(<OtaPlatformsPage />);

    await waitFor(() => {
      expect(screen.getByText('No platforms found.')).toBeInTheDocument();
    });
  });
});
