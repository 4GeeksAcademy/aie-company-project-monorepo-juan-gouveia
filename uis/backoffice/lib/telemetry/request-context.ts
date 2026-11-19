// Contexto de petición: da a track() el `requestId` de la llamada a la API que originó un evento
// (decisión C9). La capa de datos envuelve la emisión en withRequestId(); los componentes no pasan nada.
//
// Es síncrono a propósito: track() solo lee el id mientras se ejecuta `fn`. Un evento emitido fuera
// (una vista, un error de JavaScript, Web Vitals) lleva `requestId: null`, como dice el plan.

let currentId: string | null = null;

export function withRequestId<T>(requestId: string | null | undefined, fn: () => T): T {
  const previous = currentId;
  currentId = requestId ?? null;
  try {
    return fn();
  } finally {
    currentId = previous;
  }
}

export function currentRequestId(): string | null {
  return currentId;
}
