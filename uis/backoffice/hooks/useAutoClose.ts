import { useEffect, useRef } from "react";

// Llama a `onClose` una vez pasados `delayMs` desde que `active` pasa a true.
// Usa una ref para que un `onClose` nuevo en cada render no reinicie el temporizador.
export function useAutoClose(active: boolean, delayMs: number, onClose: () => void) {
  const onCloseRef = useRef(onClose);

  useEffect(() => {
    onCloseRef.current = onClose;
  });

  useEffect(() => {
    if (!active) return;
    const timeout = setTimeout(() => onCloseRef.current(), delayMs);
    return () => clearTimeout(timeout);
  }, [active, delayMs]);
}
