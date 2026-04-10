import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ApiError, api } from '../../api/client';

describe('ApiError', () => {
  it('has status, error, and message', () => {
    const err = new ApiError(404, { code: 'not_found', message: 'Not found' });
    expect(err.status).toBe(404);
    expect(err.error.code).toBe('not_found');
    expect(err.message).toBe('Not found');
    expect(err.name).toBe('ApiError');
    expect(err).toBeInstanceOf(Error);
  });
});

describe('api client', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('get sends GET request and returns json', async () => {
    const payload = { items: [], total: 0 };
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(payload), { status: 200, headers: { 'Content-Type': 'application/json' } }),
    );

    const result = await api.get<typeof payload>('/api/test');
    expect(result).toEqual(payload);
    expect(fetch).toHaveBeenCalledWith('/api/test', expect.objectContaining({ headers: expect.any(Object) }));
  });

  it('get includes auth header when token is set', async () => {
    localStorage.setItem('auth_token', 'my-jwt');
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('{}', { status: 200 }),
    );

    await api.get('/api/test');
    const call = vi.mocked(fetch).mock.calls[0];
    const headers = call[1]?.headers as Record<string, string>;
    expect(headers['Authorization']).toBe('Bearer my-jwt');
  });

  it('post sends JSON body', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('{"id": "1"}', { status: 200 }),
    );

    await api.post('/api/items', { name: 'test' });
    const call = vi.mocked(fetch).mock.calls[0];
    expect(call[1]?.method).toBe('POST');
    expect(call[1]?.body).toBe('{"name":"test"}');
    const headers = call[1]?.headers as Record<string, string>;
    expect(headers['Content-Type']).toBe('application/json');
  });

  it('put sends PUT request', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('{}', { status: 200 }),
    );

    await api.put('/api/items/1', { name: 'updated' });
    const call = vi.mocked(fetch).mock.calls[0];
    expect(call[1]?.method).toBe('PUT');
  });

  it('delete sends DELETE request', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(null, { status: 204 }),
    );

    const result = await api.delete('/api/items/1');
    expect(result).toBeUndefined();
    const call = vi.mocked(fetch).mock.calls[0];
    expect(call[1]?.method).toBe('DELETE');
  });

  it('throws ApiError on non-ok response', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ code: 'bad_request', message: 'Invalid' }), { status: 400 }),
    );

    try {
      await api.get('/api/bad');
      expect.fail('should have thrown');
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      const err = e as ApiError;
      expect(err.status).toBe(400);
      expect(err.error.code).toBe('bad_request');
    }
  });

  it('throws ApiError with fallback on non-json error response', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('Server Error', { status: 500, statusText: 'Internal Server Error' }),
    );

    await expect(api.get('/api/fail')).rejects.toThrow(ApiError);
  });

  it('upload sends FormData without Content-Type header', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('{}', { status: 200 }),
    );

    const fd = new FormData();
    fd.append('file', new Blob(['content']), 'test.zip');
    await api.upload('/api/upload', fd);

    const call = vi.mocked(fetch).mock.calls[0];
    expect(call[1]?.body).toBeInstanceOf(FormData);
    const headers = call[1]?.headers as Record<string, string>;
    expect(headers['Content-Type']).toBeUndefined();
  });
});
