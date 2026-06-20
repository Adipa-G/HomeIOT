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
  variable_defs: [
    {
      name: 'TEMP_THRESHOLD',
      type: 'number',
      default_value: '28',
      description: 'trip point',
      control_type: 'text',
      control_options: [],
      has_server_code: true,
      server_code: 'return 28;',
    },
  ],
  versions: [
    { id: 'v1', version: '1.0.0', package_hash: 'sha256:abc123def456', package_size_bytes: 256, created_at_utc: '2026-05-10T00:00:00Z' },
  ],
  assignments: [
    { id: 'a1', device_id: 'esp32-001', module_id: 'sensor-reader', version: '1.0.0', interval_ms: 60000, timeout_ms: 30000, entrypoint: 'run', enabled: true, created_at_utc: '2026-05-10T00:00:00Z', updated_at_utc: '2026-05-10T00:00:00Z' },
  ],
};

function mockModuleAndDevices() {
  vi.mocked(api.get).mockImplementation(async (path: string) => {
    if (path.startsWith('/api/admin/devices')) {
      return { items: [], total: 0, offset: 0, limit: 200 };
    }
    return mockModule;
  });
}

describe('ModuleDetailPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.setItem('auth_token', 'test-token');
  });

  it('renders module detail with versions and assignments', async () => {
    mockModuleAndDevices();
    renderWithProviders(<ModuleDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('Versions')).toBeInTheDocument();
    });
    expect(screen.getByText('Reads DHT22 sensors')).toBeInTheDocument();
    expect(screen.getAllByText('1.0.0').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('esp32-001')).toBeInTheDocument();
  });

  it('prefills module id when entering edit mode', async () => {
    const user = userEvent.setup();
    mockModuleAndDevices();
    renderWithProviders(<ModuleDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('Versions')).toBeInTheDocument();
    });

    const editButtons = screen.getAllByRole('button', { name: 'Edit' });
    await user.click(editButtons[0]);

    const moduleIdInput = screen.getByLabelText('Module ID');
    expect(moduleIdInput).toHaveValue('sensor-reader');
    expect(moduleIdInput).toBeDisabled();
  });

  it('shows File and Code upload mode toggles', async () => {
    const user = userEvent.setup();
    mockModuleAndDevices();
    renderWithProviders(<ModuleDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('Versions')).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: '+ Add Version' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '+ Add Version' }));
    expect(screen.getByRole('button', { name: 'File' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Code' })).toBeInTheDocument();
  });

  it('switches to code mode and shows textarea', async () => {
    const user = userEvent.setup();
    mockModuleAndDevices();
    renderWithProviders(<ModuleDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('Versions')).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: '+ Add Version' }));
    await user.click(screen.getByRole('button', { name: 'Code' }));
    expect(screen.getByPlaceholderText(/def run/)).toBeInTheDocument();
    expect(screen.getByText('Save Version')).toBeInTheDocument();
  });

  it('shows View button for versions to see code', async () => {
    mockModuleAndDevices();
    renderWithProviders(<ModuleDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('View')).toBeInTheDocument();
    });
  });

  it('fetches and displays code when View is clicked', async () => {
    const user = userEvent.setup();
    vi.mocked(api.get)
      .mockResolvedValueOnce(mockModule)
      .mockResolvedValueOnce({ items: [], total: 0, offset: 0, limit: 200 })
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

  it('renders variable definitions section', async () => {
    mockModuleAndDevices();
    renderWithProviders(<ModuleDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('Input Variables')).toBeInTheDocument();
    });

    expect(screen.getByText('TEMP_THRESHOLD')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '+ Add Input Variable' })).toBeInTheDocument();
  });

  it('saves a variable definition with server code', async () => {
    const user = userEvent.setup();
    mockModuleAndDevices();
    vi.mocked(api.put).mockResolvedValue({});

    renderWithProviders(<ModuleDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('Input Variables')).toBeInTheDocument();
    });

    // Open the form
    await user.click(screen.getByRole('button', { name: '+ Add Input Variable' }));

    await user.type(screen.getByPlaceholderText('e.g. TEMP_THRESHOLD'), 'WINDOW_START');
    await user.selectOptions(screen.getByLabelText('Type'), 'string');
    await user.type(screen.getByLabelText('Default value'), '08:00');
    await user.type(screen.getByLabelText('Description'), 'start time');
    await user.type(screen.getByLabelText('Server code (optional)'), 'return "08:00";');
    await user.click(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() => {
      expect(api.put).toHaveBeenCalledWith(
        '/api/admin/modules/sensor-reader/variables/WINDOW_START',
        expect.objectContaining({
          type: 'string',
          default_value: '08:00',
          description: 'start time',
          server_code: 'return "08:00";',
        }),
      );
    });
  });

  it('prefills form when editing an existing variable', async () => {
    const user = userEvent.setup();
    mockModuleAndDevices();
    renderWithProviders(<ModuleDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('TEMP_THRESHOLD')).toBeInTheDocument();
    });

    // Find the Edit button in the variables table (the last one)
    const editButtons = screen.getAllByRole('button', { name: 'Edit' });
    await user.click(editButtons[editButtons.length - 1]); // Click the last Edit button (from variables table)

    // Wait for the form to appear
    await waitFor(() => {
      expect(screen.getByPlaceholderText('e.g. TEMP_THRESHOLD')).toBeInTheDocument();
    });

    expect(screen.getByPlaceholderText('e.g. TEMP_THRESHOLD')).toHaveValue('TEMP_THRESHOLD');
    expect(screen.getByLabelText('Type')).toHaveValue('number');
    expect(screen.getByLabelText('Default value')).toHaveValue('28');
    expect(screen.getByLabelText('Description')).toHaveValue('trip point');
    expect(screen.getByLabelText('Server code (optional)')).toHaveValue('return 28;');
  });

  it('keeps existing server code when saving edited variable', async () => {
    const user = userEvent.setup();
    mockModuleAndDevices();
    vi.mocked(api.put).mockResolvedValue({});

    renderWithProviders(<ModuleDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('TEMP_THRESHOLD')).toBeInTheDocument();
    });

    // Find the Edit button in the variables table (the last one)
    const editButtons = screen.getAllByRole('button', { name: 'Edit' });
    await user.click(editButtons[editButtons.length - 1]); // Click the last Edit button (from variables table)
    
    // Wait for the form to appear
    await waitFor(() => {
      expect(screen.getByLabelText('Description')).toBeInTheDocument();
    });

    await user.clear(screen.getByLabelText('Description'));
    await user.type(screen.getByLabelText('Description'), 'new desc');
    await user.click(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() => {
      expect(api.put).toHaveBeenCalledWith(
        '/api/admin/modules/sensor-reader/variables/TEMP_THRESHOLD',
        expect.objectContaining({
          server_code: 'return 28;',
          description: 'new desc',
        }),
      );
    });
  });

  it('shows assignment schedule fields and sends them in assign payload', async () => {
    const user = userEvent.setup();
    vi.mocked(api.get).mockImplementation(async (path: string) => {
      if (path.startsWith('/api/admin/devices')) {
        return { items: [{ device_id: 'esp32-001' }], total: 1, offset: 0, limit: 200 };
      }
      return mockModule;
    });
    vi.mocked(api.post).mockResolvedValue({});

    renderWithProviders(<ModuleDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('Assignments')).toBeInTheDocument();
    });

    expect(screen.getByLabelText('Interval (ms)')).toBeInTheDocument();
    expect(screen.getByLabelText('Timeout (ms)')).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText('Device'), 'esp32-001');
    await user.selectOptions(screen.getByLabelText('Version'), '1.0.0');
    await user.type(screen.getByLabelText('Interval (ms)'), '45000');
    await user.type(screen.getByLabelText('Timeout (ms)'), '7000');
    await user.click(screen.getByRole('button', { name: 'Assign' }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        '/api/admin/modules/sensor-reader/assignments',
        expect.objectContaining({
          device_id: 'esp32-001',
          version: '1.0.0',
          interval_ms: 45000,
          timeout_ms: 7000,
        }),
      );
    });
  });

  it('displays Output Variables section when output variables exist', async () => {
    const moduleWithOutput = {
      ...mockModule,
      variable_defs: [
        ...mockModule.variable_defs,
        {
          name: 'temperature',
          type: 'json',
          description: 'sensor temperature',
          control_type: null, // OUTPUT variable
          control_options: [],
          has_server_code: false,
          server_code: null,
          inferred_json_schema: null,
        },
      ],
    };

    vi.mocked(api.get).mockImplementation(async (path: string) => {
      if (path.startsWith('/api/admin/devices')) {
        return { items: [], total: 0, offset: 0, limit: 200 };
      }
      return moduleWithOutput;
    });

    renderWithProviders(<ModuleDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('Output Variables')).toBeInTheDocument();
    });
    expect(screen.getByText('temperature')).toBeInTheDocument();
  });

  it('infers schema when Schema button is clicked', async () => {
    const user = userEvent.setup();
    const moduleWithOutput = {
      ...mockModule,
      variable_defs: [
        {
          name: 'sensor_data',
          type: 'json',
          description: 'output data',
          control_type: null,
          control_options: [],
          has_server_code: false,
          server_code: null,
          inferred_json_schema: null,
        },
      ],
    };

    vi.mocked(api.get)
      .mockResolvedValueOnce(moduleWithOutput)
      .mockResolvedValueOnce({ items: [], total: 0, offset: 0, limit: 200 });
    
    vi.mocked(api.post).mockResolvedValue({
      inferred_json_schema: { temp: 'number', status: 'string' },
    });

    renderWithProviders(<ModuleDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('sensor_data')).toBeInTheDocument();
    });

    const schemaButtons = screen.getAllByRole('button', { name: 'Schema' });
    await user.click(schemaButtons[0]);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        '/api/admin/modules/sensor-reader/variables/sensor_data/infer-schema',
        {},
      );
    });
  });

  it('shows Visualizations button for output variables', async () => {
    const user = userEvent.setup();
    const moduleWithSchema = {
      ...mockModule,
      variable_defs: [
        {
          name: 'readings',
          type: 'json',
          description: 'sensor readings',
          control_type: null,
          control_options: [],
          has_server_code: false,
          server_code: null,
          inferred_json_schema: JSON.stringify({ temperature: 'number', humidity: 'number' }),
        },
      ],
    };

    vi.mocked(api.get).mockImplementation(async (path: string) => {
      if (path.startsWith('/api/admin/devices')) {
        return { items: [], total: 0, offset: 0, limit: 200 };
      }
      return moduleWithSchema;
    });

    renderWithProviders(<ModuleDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('readings')).toBeInTheDocument();
    });

    // Check that Visualizations button is present for output variable
    const vizButtons = screen.getAllByRole('button', { name: 'Visualizations' });
    expect(vizButtons.length).toBeGreaterThan(0);
  });

  it('adds a new output variable', async () => {
    const user = userEvent.setup();
    const moduleWithOutput = {
      ...mockModule,
      variable_defs: [
        {
          name: 'temperature',
          type: 'json',
          description: 'temperature sensor',
          control_type: null,
          control_options: [],
          has_server_code: false,
          server_code: null,
          inferred_json_schema: null,
        },
      ],
    };

    vi.mocked(api.get).mockImplementation(async (path: string) => {
      if (path.startsWith('/api/admin/devices')) {
        return { items: [], total: 0, offset: 0, limit: 200 };
      }
      return moduleWithOutput;
    });
    
    vi.mocked(api.put).mockResolvedValue({});

    renderWithProviders(<ModuleDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('Output Variables')).toBeInTheDocument();
    });

    const addOutputVarButtons = screen.getAllByRole('button', { name: '+ Add Output Variable' });
    await user.click(addOutputVarButtons[0]);

    // Fill in the form with correct placeholder
    const nameInput = screen.getByPlaceholderText('e.g. SENSOR_OUTPUT');
    await user.type(nameInput, 'humidity');

    await user.click(screen.getByRole('button', { name: 'Create' }));

    await waitFor(() => {
      expect(api.put).toHaveBeenCalledWith(
        '/api/admin/modules/sensor-reader/variables/humidity',
        expect.objectContaining({
          type: 'json',
        }),
      );
    });
  });
});
