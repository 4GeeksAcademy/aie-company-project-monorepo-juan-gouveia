import { useCallback, useEffect, useRef, useState } from "react";
import { toUserMessage } from "@/lib/error-message";

// Estado de una carga de datos: el mismo en todos los bloques que piden algo a la API.
export type AsyncState<T> =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; data: T };

// Carga datos de la API con los estados de carga, error y éxito, y descarta la respuesta si el
// componente se desmonta o `load` cambia (por ejemplo, otro filtro) antes de que llegue.
// - `load` debe estar memorizada con useCallback: cada vez que cambia, se vuelve a pedir.
// - `errorMessage` es el texto si el error no trae uno pensado para el usuario (toUserMessage).
// - `reload` vuelve a mostrar la carga y pide de nuevo ("Reintentar" tras un error).
// - `refresh` pide de nuevo sin vaciar el bloque: se ve lo anterior hasta que llega lo nuevo.
// - `setData` modifica los datos ya cargados (por ejemplo, un cambio optimista en una fila).
export function useAsyncData<T>(load: () => Promise<T>, errorMessage: string) {
  const [state, setState] = useState<AsyncState<T>>({ status: "loading" });
  const [requestKey, setRequestKey] = useState(0);
  // true solo durante la petición que lanza `refresh`, para no pasar por "loading".
  const silentRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    const silent = silentRef.current;
    silentRef.current = false;

    async function run() {
      if (!silent) setState({ status: "loading" });
      try {
        const data = await load();
        if (!cancelled) setState({ status: "success", data });
      } catch (err) {
        if (!cancelled) setState({ status: "error", message: toUserMessage(err, errorMessage) });
      }
    }

    run();
    return () => {
      cancelled = true;
    };
  }, [load, errorMessage, requestKey]);

  const reload = useCallback(() => setRequestKey((key) => key + 1), []);

  const refresh = useCallback(() => {
    silentRef.current = true;
    setRequestKey((key) => key + 1);
  }, []);

  const setData = useCallback((update: (data: T) => T) => {
    setState((prev) => (prev.status === "success" ? { status: "success", data: update(prev.data) } : prev));
  }, []);

  return { state, reload, refresh, setData };
}
