import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import { DeviceModuleSettingsPanel } from '../../components/DeviceModuleSettingsPanel';
import { api } from '../../api/client';
import type { ModuleVariableDefItem } from '../../types/api';

vi.mock('../../api/client', () => ({
  api: {
    get: vi.fn(),
    put: vi.fn(),
  },
}));

describe('DeviceModuleSettingsPanel', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('shows the "Show in dashboard" toggle even when no controls are configured', async () => {
    vi.mocked(api.get).mockResolvedValue([]);
    renderWithProviders(
      <DeviceModuleSettingsPanel
        moduleId="sensor-reader"
        assignmentId="a1"
        variableDefs={[]}
        variableValues={[]}
        showInDashboard={false}
        onClose={vi.fn()}
      />
    );

    expect(await screen.findByText('Show in dashboard')).toBeInTheDocument();
    expect(screen.getByText('No controls configured for this module.')).toBeInTheDocument();
    const checkbox = screen.getByRole('checkbox') as HTMLInputElement;
    expect(checkbox.checked).toBe(false);
  });

  it('shows the "Show in dashboard" toggle alongside controls', async () => {
    const variableDefs: ModuleVariableDefItem[] = [
      {
        name: 'threshold',
        type: 'number',
        default_value: '25',
        description: 'Threshold',
        has_server_code: false,
        control_type: 'text',
      },
    ];
    vi.mocked(api.get).mockResolvedValue([
      { variable_name: 'threshold', value: '25', source: 'default' },
    ]);

    renderWithProviders(
      <DeviceModuleSettingsPanel
        moduleId="sensor-reader"
        assignmentId="a1"
        variableDefs={variableDefs}
        variableValues={[]}
        showInDashboard={true}
        onClose={vi.fn()}
      />
    );

    expect(await screen.findByText('Show in dashboard')).toBeInTheDocument();
    const checkbox = screen.getByRole('checkbox') as HTMLInputElement;
    expect(checkbox.checked).toBe(true);
  });

  it('sends a PUT request when the toggle is changed', async () => {
    vi.mocked(api.get).mockResolvedValue([]);
    vi.mocked(api.put).mockResolvedValue({});

    const user = userEvent.setup();
    renderWithProviders(
      <DeviceModuleSettingsPanel
        moduleId="sensor-reader"
        assignmentId="a1"
        variableDefs={[]}
        variableValues={[]}
        showInDashboard={false}
        onClose={vi.fn()}
      />
    );

    const checkbox = await screen.findByRole('checkbox');
    await user.click(checkbox);

    await waitFor(() => {
      expect(api.put).toHaveBeenCalledWith('/api/admin/modules/assignments/a1', { show_in_dashboard: true });
    });
  });
});
