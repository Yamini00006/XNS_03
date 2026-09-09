// src/hooks/usePolling.js
import { useEffect, useRef, useState } from "react";

/**
 * Polls `fetcher()` every `intervalMs` until `isDone(data)` returns true,
 * or the component unmounts. Never polls "unnecessarily" once done.
 */
export function usePolling(fetcher, { intervalMs = 3000, isDone, enabled = true } = {}) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const timerRef = useRef(null);

  useEffect(() => {
    if (!enabled) return undefined;
    let cancelled = false;

    const tick = async () => {
      try {
        const result = await fetcher();
        if (cancelled) return;
        setData(result);
        setError(null);
        if (isDone && isDone(result)) {
          return; // stop — do not schedule another tick
        }
      } catch (err) {
        if (!cancelled) setError(err);
      }
      if (!cancelled) {
        timerRef.current = setTimeout(tick, intervalMs);
      }
    };

    tick();

    return () => {
      cancelled = true;
      if (timerRef.current) clearTimeout(timerRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled]);

  return { data, error };
}
