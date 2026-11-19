/**
 * @jest-environment jsdom
 */
// Navegación y abandono de flujos: `form_validation_failed`, `form_abandoned`, `list_filter_applied`
// y `list_page_extended`. Lógica pura y los hooks montados con react-dom y `act`. track() simulado.
import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { useFormTelemetry } from "@/hooks/useFormTelemetry";
import { useListFilterTelemetry } from "@/hooks/useListFilterTelemetry";
import { useShowMore } from "@/hooks/useShowMore";
import { handleHide } from "@/lib/telemetry/lifecycle";
import { changedFilterEvents, createFormSession } from "@/lib/telemetry/navigation";

const track = jest.fn();
jest.mock("@/lib/telemetry", () => ({ track: (...args: unknown[]) => track(...args) }));

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root;

beforeEach(() => {
  track.mockReset();
  root = createRoot(document.createElement("div"));
});

afterEach(() => {
  act(() => root.unmount());
  jest.useRealTimers();
});

function events(name: string) {
  return track.mock.calls.filter(([eventType]) => eventType === name).map(([, properties]) => properties);
}

describe("sesión de un formulario", () => {
  it("un abandono lleva el último campo, los campos tocados y el tiempo, sin valores", () => {
    const session = createFormSession("outbound_order");
    session.change("ingredient_id", 0);
    session.change("quantity", 10_000);
    session.change("quantity", 20_000);

    expect(session.abandon("navigation", 48_000)).toEqual({
      form_id: "outbound_order",
      last_field: "quantity",
      filled_field_count: 2,
      time_in_form_seconds: 48,
      exit: "navigation",
    });
    // Se emite una sola vez.
    expect(session.abandon("navigation", 50_000)).toBeNull();
  });

  it("sin tocar ningún campo, o tras un envío correcto, no hay abandono", () => {
    expect(createFormSession("login").abandon("navigation", 0)).toBeNull();

    const sent = createFormSession("inbound_order");
    sent.change("quantity", 0);
    sent.succeed();
    expect(sent.abandon("navigation", 1_000)).toBeNull();
  });

  it("los errores de validación dan los campos con error, uno por formulario cada 2 s", () => {
    const session = createFormSession("incident");
    const errors = { title: "Escribe el título.", category: "Elige la categoría.", origin: undefined };

    expect(session.invalid(errors, 0)).toEqual({ form_id: "incident", invalid_fields: ["title", "category"], error_count: 2 });
    expect(session.invalid(errors, 1_000)).toBeNull();
    expect(session.invalid(errors, 2_500)).not.toBeNull();
    expect(session.invalid({}, 10_000)).toBeNull();
  });
});

describe("useFormTelemetry", () => {
  function mount(exit?: "navigation" | "modal_closed") {
    const api: { current: ReturnType<typeof useFormTelemetry> | null } = { current: null };
    function Probe() {
      api.current = useFormTelemetry("supplier", exit);
      return null;
    }
    act(() => root.render(createElement(Probe)));
    return api;
  }

  it("al desmontar un formulario empezado emite form_abandoned con su forma de salida", () => {
    const form = mount("modal_closed");
    form.current?.fieldChanged("name");

    act(() => root.unmount());
    root = createRoot(document.createElement("div"));

    expect(events("form_abandoned")).toEqual([expect.objectContaining({ form_id: "supplier", last_field: "name", exit: "modal_closed" })]);
  });

  it("al cerrar la pestaña emite el abandono como tab_closed, una sola vez", () => {
    const form = mount();
    form.current?.fieldChanged("rate_per_unit");

    handleHide();
    act(() => root.unmount());
    root = createRoot(document.createElement("div"));

    expect(events("form_abandoned")).toEqual([expect.objectContaining({ exit: "tab_closed" })]);
  });

  it("validationFailed emite form_validation_failed", () => {
    const form = mount();
    form.current?.validationFailed({ name: "Escribe el nombre." });

    expect(events("form_validation_failed")).toEqual([{ form_id: "supplier", invalid_fields: ["name"], error_count: 1 }]);
  });
});

describe("filtros de las listas", () => {
  it("un filtro de lista cerrada lleva su valor; uno de texto, solo la longitud", () => {
    expect(changedFilterEvents("order_history", { kind: "", ingredient: "" }, { kind: "exit", ingredient: "falda" }, 13, ["ingredient"])).toEqual([
      { list_id: "order_history", filter_name: "kind", filter_value: "exit", query_length: undefined, result_count: 13 },
      { list_id: "order_history", filter_name: "ingredient", filter_value: undefined, query_length: 5, result_count: 13 },
    ]);
  });

  it("al quitar un filtro no hay valor", () => {
    expect(changedFilterEvents("supplier_directory", { country: "USA" }, { country: "" }, 15)).toEqual([
      { list_id: "supplier_directory", filter_name: "country", filter_value: undefined, query_length: undefined, result_count: 15 },
    ]);
  });

  it("useListFilterTelemetry espera 500 ms y a que la lista tenga resultado; el estado inicial no cuenta", () => {
    jest.useFakeTimers();
    function Probe(props: { status: string; count: number | null }) {
      useListFilterTelemetry("incident_manager", { status: props.status, origin: "", branch: "" }, props.count);
      return null;
    }
    const render = (status: string, count: number | null) => act(() => root.render(createElement(Probe, { status, count })));

    render("", 100);
    act(() => jest.advanceTimersByTime(1_000));
    expect(track).not.toHaveBeenCalled();

    render("open", null); // cargando
    act(() => jest.advanceTimersByTime(1_000));
    expect(track).not.toHaveBeenCalled();

    render("open", 12);
    act(() => jest.advanceTimersByTime(499));
    expect(track).not.toHaveBeenCalled();
    act(() => jest.advanceTimersByTime(1));
    expect(events("list_filter_applied")).toEqual([
      { list_id: "incident_manager", filter_name: "status", filter_value: "open", query_length: undefined, result_count: 12 },
    ]);
  });
});

describe("list_page_extended", () => {
  it("cada Mostrar más emite hasta dónde llega la lista", () => {
    const api: { current: ReturnType<typeof useShowMore> | null } = { current: null };
    function Probe() {
      api.current = useShowMore(120, "k", 50, { listId: "order_history", filtersActive: true });
      return null;
    }
    act(() => root.render(createElement(Probe)));

    act(() => api.current?.showMore());
    act(() => api.current?.showMore());

    expect(events("list_page_extended")).toEqual([
      { list_id: "order_history", visible_rows: 100, total_rows: 120, filters_active: true },
      { list_id: "order_history", visible_rows: 120, total_rows: 120, filters_active: true },
    ]);
  });
});
