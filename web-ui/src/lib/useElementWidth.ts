import { useEffect, useRef, useState } from 'react';

/**
 * Tracks an element's rendered width (via ResizeObserver), starting from `fallback`.
 */
export function useElementWidth<T extends HTMLElement>(fallback: number) {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(fallback);
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof ResizeObserver === 'undefined') return;
    const update = () => {
      if (el.clientWidth > 0) setWidth(el.clientWidth);
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  return [ref, width] as const;
}
