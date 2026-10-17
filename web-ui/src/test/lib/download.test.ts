import { describe, it, expect, vi, afterEach } from 'vitest';
import { downloadTextFile } from '../../lib/download';

describe('downloadTextFile', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('downloads the content as a named file and releases the object URL', async () => {
    const createObjectURL = vi.fn(() => 'blob:fake');
    const revokeObjectURL = vi.fn();
    vi.stubGlobal('URL', { ...URL, createObjectURL, revokeObjectURL });
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) {
      expect(this.download).toBe('main.py');
      expect(this.getAttribute('href')).toBe('blob:fake');
    });

    downloadTextFile('main.py', 'print(1)\n');

    expect(click).toHaveBeenCalledOnce();
    const blob = (createObjectURL.mock.calls[0] as unknown as [Blob])[0];
    expect(await blob.text()).toBe('print(1)\n');
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:fake');
    expect(document.querySelector('a[download]')).toBeNull();
  });
});
