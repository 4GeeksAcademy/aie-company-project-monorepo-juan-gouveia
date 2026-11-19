// Ciclo de vida de la página para la telemetría: qué hacer cuando la pestaña se oculta o se cierra.
//
// Orden: primero las tareas registradas con onBeforeHide() (p. ej. emitir las métricas de carga de
// la vista, que solo son definitivas en ese momento) y después el envío con sendBeacon de todo lo
// pendiente, incluido lo que acaban de emitir.
//
// El listener va en `window` y no en `document`: `visibilitychange` sube desde document hasta window,
// así que se ejecuta después de los listeners de document, entre ellos los de Web Vitals, que
// entregan CLS e INP justo al ocultarse la pestaña.

const beforeHide = new Set<() => void>();
let beaconFlush: (() => void) | null = null;
let listening = false;

export function onBeforeHide(task: () => void): () => void {
  beforeHide.add(task);
  return () => beforeHide.delete(task);
}

// La cola registra aquí su envío con sendBeacon cuando se crea.
export function setBeaconFlush(flush: () => void): void {
  beaconFlush = flush;
}

// Envía ya lo pendiente con sendBeacon (si hay cola).
export function flushWithBeaconNow(): void {
  beaconFlush?.();
}

export function handleHide(): void {
  for (const task of beforeHide) {
    try {
      task();
    } catch {
      // Una tarea que falla no impide enviar lo pendiente.
    }
  }
  flushWithBeaconNow();
}

export function listenForHide(): void {
  if (listening || typeof window === "undefined") return;
  listening = true;
  window.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") handleHide();
  });
  // pagehide cubre los navegadores que no emiten visibilitychange al cerrar la página.
  window.addEventListener("pagehide", handleHide);
}
