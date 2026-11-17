/**
 * @jest-environment jsdom
 */
// Hook genérico de carga de datos (R1 de audit/AUDIT.md). Se monta con react-dom y `act` de React,
// sin librerías extra: un componente mínimo guarda en `latest` lo que devuelve el hook.
import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { useAsyncData, type AsyncState } from "@/hooks/useAsyncData";
import { ApiError } from "@/lib/api-client";

// React solo aplica `act` sin avisos si el entorno lo declara.
(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

type HookResult<T> = ReturnType<typeof useAsyncData<T>>;

// Promesa que la prueba resuelve o rechaza cuando quiere.
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

let root: Root;
let container: HTMLDivElement;

beforeEach(() => {
  container = document.createElement("div");
  root = createRoot(container);
});

afterEach(() => {
  act(() => root.unmount());
});

function renderHook<T>(load: () => Promise<T>, errorMessage = "Falló la carga.") {
  const result: { current: HookResult<T> | null } = { current: null };
  function Probe({ loader }: { loader: () => Promise<T> }) {
    result.current = useAsyncData(loader, errorMessage);
    return null;
  }
  const render = (loader: () => Promise<T>) => act(() => root.render(createElement(Probe, { loader })));
  render(load);
  return { result, rerender: render };
}

const stateOf = <T>(result: { current: HookResult<T> | null }): AsyncState<T> => result.current!.state;

describe("useAsyncData", () => {
  test("empieza en loading y pasa a success con los datos", async () => {
    const request = deferred<string[]>();
    const { result } = renderHook(() => request.promise);
    expect(stateOf(result)).toEqual({ status: "loading" });

    await act(async () => request.resolve(["a", "b"]));
    expect(stateOf(result)).toEqual({ status: "success", data: ["a", "b"] });
  });

  test("muestra el mensaje de la API si el error lo trae", async () => {
    const { result } = renderHook(() => Promise.reject(new ApiError("La API no responde.", 503, "service_unavailable")));
    await act(async () => {});
    expect(stateOf(result)).toEqual({ status: "error", message: "La API no responde." });
  });

  test("usa el texto de respaldo si el error no es para el usuario", async () => {
    const { result } = renderHook(() => Promise.reject(new TypeError("fetch failed")), "No se pudo cargar.");
    await act(async () => {});
    expect(stateOf(result)).toEqual({ status: "error", message: "No se pudo cargar." });
  });

  test("reload vuelve a loading y pide de nuevo", async () => {
    const load = jest.fn().mockRejectedValueOnce(new TypeError("x")).mockResolvedValueOnce(42);
    const { result } = renderHook<number>(load);
    await act(async () => {});
    expect(stateOf(result).status).toBe("error");

    act(() => result.current!.reload());
    expect(stateOf(result)).toEqual({ status: "loading" });
    await act(async () => {});
    expect(stateOf(result)).toEqual({ status: "success", data: 42 });
    expect(load).toHaveBeenCalledTimes(2);
  });

  test("refresh pide de nuevo sin pasar por loading", async () => {
    const second = deferred<number>();
    const load = jest.fn().mockResolvedValueOnce(1).mockReturnValueOnce(second.promise);
    const { result } = renderHook<number>(load);
    await act(async () => {});

    act(() => result.current!.refresh());
    expect(stateOf(result)).toEqual({ status: "success", data: 1 });
    await act(async () => second.resolve(2));
    expect(stateOf(result)).toEqual({ status: "success", data: 2 });
  });

  test("descarta la respuesta anterior si cambia la función de carga", async () => {
    const first = deferred<string>();
    const second = deferred<string>();
    const { result, rerender } = renderHook(() => first.promise);

    rerender(() => second.promise);
    await act(async () => second.resolve("nuevo"));
    await act(async () => first.resolve("viejo"));
    expect(stateOf(result)).toEqual({ status: "success", data: "nuevo" });
  });

  test("setData modifica los datos cargados y no hace nada mientras carga", async () => {
    const request = deferred<number[]>();
    const { result } = renderHook(() => request.promise);

    act(() => result.current!.setData((rows) => [...rows, 99]));
    expect(stateOf(result)).toEqual({ status: "loading" });

    await act(async () => request.resolve([1, 2]));
    act(() => result.current!.setData((rows) => rows.map((n) => n * 10)));
    expect(stateOf(result)).toEqual({ status: "success", data: [10, 20] });
  });
});
