/**
 * @jest-environment jsdom
 */
// Lista pintada por partes (historial de órdenes y gestor de incidencias). Se monta con react-dom y
// `act`, como use-async-data.test.ts.
import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { useShowMore } from "@/hooks/useShowMore";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

type HookResult = ReturnType<typeof useShowMore>;

let root: Root;

beforeEach(() => {
  root = createRoot(document.createElement("div"));
});

afterEach(() => {
  act(() => root.unmount());
});

function renderHook(total: number, resetKey: string) {
  const result: { current: HookResult | null } = { current: null };
  function Probe(props: { total: number; resetKey: string }) {
    result.current = useShowMore(props.total, props.resetKey);
    return null;
  }
  const render = (nextTotal: number, nextKey: string) =>
    act(() => root.render(createElement(Probe, { total: nextTotal, resetKey: nextKey })));
  render(total, resetKey);
  return { result, rerender: render };
}

describe("useShowMore", () => {
  test("empieza con 50 filas y añade 50 en cada clic", () => {
    const { result } = renderHook(120, "");
    expect(result.current).toMatchObject({ visible: 50, hasMore: true, nextCount: 50 });

    act(() => result.current!.showMore());
    expect(result.current).toMatchObject({ visible: 100, hasMore: true, nextCount: 20 });

    act(() => result.current!.showMore());
    expect(result.current).toMatchObject({ visible: 120, hasMore: false, nextCount: 0 });
  });

  test("con menos de 50 filas las muestra todas y no ofrece más", () => {
    const { result } = renderHook(12, "");
    expect(result.current).toMatchObject({ visible: 12, hasMore: false, nextCount: 0 });
  });

  test("vuelve a 50 filas cuando cambia la clave (otros filtros)", () => {
    const { result, rerender } = renderHook(500, "open||");
    act(() => result.current!.showMore());
    act(() => result.current!.showMore());
    expect(result.current!.visible).toBe(150);

    rerender(300, "resolved||");
    expect(result.current).toMatchObject({ visible: 50, nextCount: 50 });
  });

  test("no se pliega si cambian los datos con la misma clave (cambio de estado de una fila)", () => {
    const { result, rerender } = renderHook(500, "||");
    act(() => result.current!.showMore());
    act(() => result.current!.showMore());

    rerender(500, "||");
    expect(result.current!.visible).toBe(150);
  });

  test("si la lista se acorta, no muestra más filas de las que hay", () => {
    const { result, rerender } = renderHook(500, "||");
    act(() => result.current!.showMore());

    rerender(70, "||");
    expect(result.current).toMatchObject({ visible: 70, hasMore: false, nextCount: 0 });
  });
});
