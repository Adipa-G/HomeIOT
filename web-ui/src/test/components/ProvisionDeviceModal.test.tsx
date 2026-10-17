import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ProvisionDeviceModal } from '../../components/ProvisionDeviceModal';
import { api, ApiError } from '../../api/client';
import { downloadTextFile } from '../../lib/download';

vi.mock('../../api/client', async () => {
  const actual = await vi.importActual<typeof import('../../api/client')>('../../api/client');
  return { ...actual, api: { post: vi.fn() } };
});

vi.mock('../../lib/download', () => ({ downloadTextFile: vi.fn() }));

const response = {
  device_id: 'esp32-kitchen',
  platform: 'esp32',
  release_version: '1.4.0',
  file_name: 'main.py',
  script: '# script',
};

async function fillCreateForm(user: ReturnType<typeof userEvent.setup>, deviceId = 'esp32-kitchen') {
  await user.type(screen.getByLabelText('Device ID'), deviceId);
  await user.type(screen.getByLabelText('WiFi SSID'), 'Home WiFi');
  await user.type(screen.getByLabelText('WiFi password'), 'secret');
}

describe('ProvisionDeviceModal', () => {
  beforeEach(() => {
    vi.mocked(api.post).mockReset();
    vi.mocked(downloadTextFile).mockReset();
  });

  it('creates a device, downloads main.py and shows setup steps', async () => {
    const user = userEvent.setup();
    const onProvisioned = vi.fn();
    vi.mocked(api.post).mockResolvedValue(response);
    render(<ProvisionDeviceModal onClose={vi.fn()} onProvisioned={onProvisioned} />);

    expect(screen.getByLabelText('API URL (reachable from the device)')).toHaveValue(window.location.origin);
    await fillCreateForm(user);
    await user.selectOptions(screen.getByLabelText('Platform'), 'pico');
    await user.click(screen.getByRole('button', { name: 'Create & download main.py' }));

    await waitFor(() => expect(screen.getByText(/has been downloaded/)).toBeInTheDocument());
    expect(api.post).toHaveBeenCalledWith('/api/admin/devices', {
      device_id: 'esp32-kitchen',
      platform: 'pico',
      api_url: window.location.origin,
      wifi_ssid: 'Home WiFi',
      wifi_password: 'secret',
    });
    expect(downloadTextFile).toHaveBeenCalledWith('main.py', '# script');
    expect(onProvisioned).toHaveBeenCalledWith(response);
    expect(screen.getByText(/contains the device API key and WiFi password/)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Download again' }));
    expect(downloadTextFile).toHaveBeenCalledTimes(2);
  });

  it('validates the device id before calling the API', async () => {
    const user = userEvent.setup();
    render(<ProvisionDeviceModal onClose={vi.fn()} />);

    await fillCreateForm(user, 'bad id!');
    await user.click(screen.getByRole('button', { name: 'Create & download main.py' }));

    expect(screen.getByRole('alert')).toHaveTextContent('Device ID may only contain');
    expect(api.post).not.toHaveBeenCalled();
  });

  it('requires an http(s) API URL and an SSID', async () => {
    const user = userEvent.setup();
    render(<ProvisionDeviceModal onClose={vi.fn()} />);

    await user.type(screen.getByLabelText('Device ID'), 'dev-1');
    await user.click(screen.getByRole('button', { name: 'Create & download main.py' }));
    expect(screen.getByRole('alert')).toHaveTextContent('WiFi SSID is required.');

    const url = screen.getByLabelText('API URL (reachable from the device)');
    await user.clear(url);
    await user.type(url, 'hub.local');
    await user.click(screen.getByRole('button', { name: 'Create & download main.py' }));
    expect(screen.getByRole('alert')).toHaveTextContent('API URL must start with http');
    expect(api.post).not.toHaveBeenCalled();
  });

  it('shows the API error message when provisioning fails', async () => {
    const user = userEvent.setup();
    vi.mocked(api.post).mockRejectedValue(
      new ApiError(409, { code: 'no_release', message: "No firmware release uploaded for platform 'esp32'." }),
    );
    render(<ProvisionDeviceModal onClose={vi.fn()} />);

    await fillCreateForm(user);
    await user.click(screen.getByRole('button', { name: 'Create & download main.py' }));

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('No firmware release uploaded'));
    expect(downloadTextFile).not.toHaveBeenCalled();
  });

  it('re-provisions an existing device without asking for the device id', async () => {
    const user = userEvent.setup();
    vi.mocked(api.post).mockResolvedValue({ ...response, device_id: 'pico 1', platform: 'pico' });
    render(<ProvisionDeviceModal deviceId="pico 1" defaultPlatform="pico" onClose={vi.fn()} />);

    expect(screen.queryByLabelText('Device ID')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Platform')).toHaveValue('pico');
    await user.type(screen.getByLabelText('WiFi SSID'), 'Home');
    await user.click(screen.getByRole('button', { name: 'Rotate key & download main.py' }));

    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith('/api/admin/devices/pico%201/provision', {
        platform: 'pico',
        api_url: window.location.origin,
        wifi_ssid: 'Home',
        wifi_password: '',
      }),
    );
  });

  it('calls onClose when cancelled', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<ProvisionDeviceModal onClose={onClose} />);

    await user.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(onClose).toHaveBeenCalled();
  });
});
