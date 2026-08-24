const brasaApi = window.brasaManual;

const resultTitle = document.getElementById("mt-result-title");
const resultMeta = document.getElementById("mt-result-meta");
const resultJson = document.getElementById("mt-result-json");

const setResult = (title, payload) => {
  if (!resultTitle || !resultMeta || !resultJson) {
    return;
  }

  resultTitle.textContent = title;

  if (Array.isArray(payload)) {
    resultMeta.textContent = `Registros: ${payload.length}`;
  } else if (payload && typeof payload === "object" && "valid" in payload && "errors" in payload) {
    const valid = payload.valid;
    const errors = payload.errors;
    resultMeta.textContent = `Valido: ${valid ? "si" : "no"} | Errores: ${Array.isArray(errors) ? errors.length : 0}`;
  } else {
    resultMeta.textContent = "";
  }

  resultJson.textContent = JSON.stringify(payload, null, 2);
};

const wire = (id, title, fn) => {
  const button = document.getElementById(id);
  if (!button) {
    return;
  }

  button.addEventListener("click", () => {
    if (!brasaApi) {
      setResult("Error", { message: "No se encontro window.brasaManual. Compila con tsc -p src/utils/tsconfig.manual.json" });
      return;
    }

    try {
      setResult(title, fn());
    } catch (error) {
      setResult(`Error en ${title}`, {
        message: error instanceof Error ? error.message : String(error),
      });
    }
  });
};

wire("mt-run-sales-by-location", "Ventas por locacion", () => {
  const locationId = document.getElementById("mt-location-id")?.value || "";
  return brasaApi.filters.salesByLocation(locationId);
});

wire("mt-run-sales-by-range", "Ventas por rango de fechas", () => {
  const startDate = document.getElementById("mt-start-date")?.value || "";
  const endDate = document.getElementById("mt-end-date")?.value || "";
  return brasaApi.filters.salesByDateRange(startDate, endDate);
});

wire("mt-run-menu-by-category", "Items por categoria", () => {
  const category = document.getElementById("mt-category")?.value || "Meat";
  return brasaApi.filters.menuByCategory(category);
});

wire("mt-run-active-locations", "Locaciones activas", () => brasaApi.filters.activeLocations());

wire("mt-run-location-by-id", "Busqueda de locacion por ID", () => {
  const id = document.getElementById("mt-search-location-id")?.value || "";
  return brasaApi.search.locationById(id);
});

wire("mt-run-item-by-name", "Busqueda de item por nombre", () => {
  const name = document.getElementById("mt-search-item-name")?.value || "";
  return brasaApi.search.menuItemByName(name);
});

wire("mt-run-binary-capacity", "Busqueda binaria por capacidad", () => {
  const capacityValue = document.getElementById("mt-target-capacity")?.value || "0";
  return brasaApi.search.locationCapacityBinary(Number(capacityValue));
});

wire("mt-run-sort-locations", "Locaciones ordenadas por capacidad", () => {
  const order = document.getElementById("mt-order-sort")?.value || "asc";
  return brasaApi.sort.locationsByCapacity(order);
});

wire("mt-run-sort-menu", "Items ordenados por precio", () => {
  const currency = document.getElementById("mt-currency-sort")?.value || "USD";
  const order = document.getElementById("mt-order-sort")?.value || "asc";
  return brasaApi.sort.menuItemsByPrice(currency, order);
});

wire("mt-run-daily-revenue", "Revenue diario", () => {
  const date = document.getElementById("mt-report-date")?.value || "";
  const currency = document.getElementById("mt-report-currency")?.value || "USD";
  return brasaApi.reports.dailyRevenue(date, currency);
});

wire("mt-run-average-ticket", "Ticket promedio", () => {
  const currency = document.getElementById("mt-report-currency")?.value || "USD";
  return brasaApi.reports.averageTicket(currency);
});

wire("mt-run-payment-method", "Ventas por metodo de pago", () => brasaApi.reports.salesByPaymentMethod());

wire("mt-run-top-items", "Top items vendidos", () => {
  const topNValue = document.getElementById("mt-top-n")?.value || "0";
  return brasaApi.reports.topSellingItems(Number(topNValue));
});

wire("mt-run-country-comparison", "Comparativa por pais", () => brasaApi.reports.countryComparison());
wire("mt-run-location-ranking", "Ranking de locaciones", () => brasaApi.reports.locationRanking());

wire("mt-run-validate-menu", "Validacion de menu item", () => brasaApi.validations.menuItem());
wire("mt-run-validate-sale", "Validacion de venta", () => brasaApi.validations.sale());
wire("mt-run-validate-location", "Validacion de locacion", () => brasaApi.validations.location());

if (!brasaApi) {
  setResult("Estado inicial", {
    message: "No se encontro window.brasaManual. Ejecuta primero: tsc -p src/utils/tsconfig.manual.json",
  });
} else {
  setResult("Estado inicial", {
    message: "Panel listo. Usa los botones para ejecutar operaciones.",
    dataset: {
      menuItems: brasaApi.dataset.sampleMenuItems.length,
      sales: brasaApi.dataset.sampleSales.length,
      locations: brasaApi.dataset.sampleLocations.length,
      wasteRecords: brasaApi.dataset.sampleWasteRecords.length,
    },
  });
}
