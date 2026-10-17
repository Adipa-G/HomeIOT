import { useState, type FormEvent } from 'react';
import { api, ApiError } from '../api/client';
import { downloadTextFile } from '../lib/download';
import type {
  CreateDeviceRequest,
  ProvisionablePlatform,
  ProvisionDeviceResponse,
  ReprovisionDeviceRequest,
} from '../types/api';

const PLATFORMS: ProvisionablePlatform[] = ['esp32', 'pico'];
const DEVICE_ID_PATTERN = /^[A-Za-z0-9._-]{1,64}$/;

interface Props {
  /** When set, the modal re-provisions this existing device (rotating its API key). */
  deviceId?: string;
  defaultPlatform?: string | null;
  onClose: () => void;
  onProvisioned?: (response: ProvisionDeviceResponse) => void;
}

function asPlatform(value: string | null | undefined): ProvisionablePlatform {
  return PLATFORMS.includes(value as ProvisionablePlatform) ? (value as ProvisionablePlatform) : 'esp32';
}

export function ProvisionDeviceModal({ deviceId, defaultPlatform, onClose, onProvisioned }: Props) {
  const isReprovision = deviceId !== undefined;
  const [newDeviceId, setNewDeviceId] = useState('');
  const [platform, setPlatform] = useState<ProvisionablePlatform>(asPlatform(defaultPlatform));
  const [apiUrl, setApiUrl] = useState(() => (typeof window !== 'undefined' ? window.location.origin : ''));
  const [wifiSsid, setWifiSsid] = useState('');
  const [wifiPassword, setWifiPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<ProvisionDeviceResponse | null>(null);

  const validate = (): string | null => {
    if (!isReprovision && !DEVICE_ID_PATTERN.test(newDeviceId.trim()))
      return "Device ID may only contain letters, digits, '.', '_' or '-' (max 64).";
    if (!/^https?:\/\/\S+$/i.test(apiUrl.trim())) return 'API URL must start with http:// or https://.';
    if (!wifiSsid) return 'WiFi SSID is required.';
    return null;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setError(null);
    setSubmitting(true);
    try {
      const connection = { api_url: apiUrl.trim(), wifi_ssid: wifiSsid, wifi_password: wifiPassword };
      const response = isReprovision
        ? await api.post<ProvisionDeviceResponse>(
            `/api/admin/devices/${encodeURIComponent(deviceId)}/provision`,
            { ...connection, platform } satisfies ReprovisionDeviceRequest,
          )
        : await api.post<ProvisionDeviceResponse>(
            '/api/admin/devices',
            { ...connection, device_id: newDeviceId.trim(), platform } satisfies CreateDeviceRequest,
          );
      // The WiFi password only needs to live long enough to build the script.
      setWifiPassword('');
      setResult(response);
      downloadTextFile(response.file_name, response.script);
      onProvisioned?.(response);
    } catch (err) {
      setError(err instanceof ApiError || err instanceof Error ? err.message : 'Provisioning failed.');
    } finally {
      setSubmitting(false);
    }
  };

  const inputClass = 'mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none';
  const title = isReprovision ? `Re-provision ${deviceId}` : 'Add device';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" role="dialog" aria-modal="true" aria-label={title}>
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-lg">
        <h3 className="text-lg font-semibold text-gray-900">{title}</h3>

        {result ? (
          <div className="mt-4 space-y-3 text-sm text-gray-700">
            <p>
              <strong>{result.file_name}</strong> for <strong>{result.device_id}</strong> ({result.platform}, firmware{' '}
              {result.release_version}) has been downloaded.
            </p>
            <ol className="list-decimal space-y-1 pl-5">
              <li>Flash MicroPython onto the {result.platform} board.</li>
              <li>Copy <code>{result.file_name}</code> to the root of the device (e.g. <code>mpremote cp {result.file_name} :</code>).</li>
              <li>Reset the device. It will join WiFi, install firmware {result.release_version} and register itself.</li>
            </ol>
            <p className="rounded border border-yellow-200 bg-yellow-50 px-3 py-2 text-xs text-yellow-800">
              This file contains the device API key and WiFi password. Delete it after copying it to the device.
            </p>
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => downloadTextFile(result.file_name, result.script)}
                className="rounded border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50"
              >
                Download again
              </button>
              <button type="button" onClick={onClose} className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700">
                Done
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-4 space-y-3" noValidate>
            {isReprovision && (
              <p className="rounded border border-yellow-200 bg-yellow-50 px-3 py-2 text-xs text-yellow-800">
                A new API key will be generated. The device will stop authenticating until the new <code>main.py</code> is
                installed on it.
              </p>
            )}
            {!isReprovision && (
              <label className="block text-sm font-medium text-gray-700">
                Device ID
                <input
                  type="text"
                  value={newDeviceId}
                  onChange={(e) => setNewDeviceId(e.target.value)}
                  placeholder="esp32-kitchen"
                  className={inputClass}
                  autoFocus
                />
              </label>
            )}
            <label className="block text-sm font-medium text-gray-700">
              Platform
              <select value={platform} onChange={(e) => setPlatform(e.target.value as ProvisionablePlatform)} className={inputClass}>
                {PLATFORMS.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </label>
            <label className="block text-sm font-medium text-gray-700">
              API URL (reachable from the device)
              <input type="url" value={apiUrl} onChange={(e) => setApiUrl(e.target.value)} className={inputClass} />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              WiFi SSID
              <input type="text" value={wifiSsid} onChange={(e) => setWifiSsid(e.target.value)} className={inputClass} autoComplete="off" />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              WiFi password
              <input
                type="password"
                value={wifiPassword}
                onChange={(e) => setWifiPassword(e.target.value)}
                className={inputClass}
                autoComplete="new-password"
              />
            </label>
            <p className="text-xs text-gray-500">WiFi credentials are embedded in the generated file and are not stored on the server.</p>

            {error && <p className="text-sm text-red-600" role="alert">{error}</p>}

            <div className="flex justify-end gap-3 pt-2">
              <button type="button" onClick={onClose} className="rounded border border-gray-300 px-4 py-2 text-sm">
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {submitting ? 'Generating…' : isReprovision ? 'Rotate key & download main.py' : 'Create & download main.py'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
