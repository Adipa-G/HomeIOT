import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import AssignmentVariablesPanel from '../../components/AssignmentVariablesPanel';

describe('AssignmentVariablesPanel', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('fetches variables, shows editable input, and sends PUT on save', async () => {
    const payload = [
      { variable_name: 'TEMP_THRESHOLD', value: '25', source: 'default', last_computed_at_utc: null },
    ];

    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify(payload), { status: 200, headers: { 'Content-Type': 'application/json' } }))
      .mockResolvedValueOnce(new Response(JSON.stringify({}), { status: 200, headers: { 'Content-Type': 'application/json' } }));

    const user = userEvent.setup();
    renderWithProviders(<AssignmentVariablesPanel assignmentId={'00000000-0000-0000-0000-000000000000'} />);

    const input = await screen.findByDisplayValue('25');
    expect(screen.getByText('TEMP_THRESHOLD')).toBeInTheDocument();

    await user.clear(input);
    await user.type(input, '30');

    await user.click(screen.getByText('Save'));

    const call = vi.mocked(fetch).mock.calls[1];
    expect(call[0]).toContain('/api/admin/modules/assignments/00000000-0000-0000-0000-000000000000/variables/TEMP_THRESHOLD');
    expect(call[1]?.method).toBe('PUT');
    expect(call[1]?.body).toBe(JSON.stringify({ value: '30' }));
  });
});
