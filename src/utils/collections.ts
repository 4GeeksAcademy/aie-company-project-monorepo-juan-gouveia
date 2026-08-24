// Funciones para filtrar datos de Brasaland

import type { Location, MenuCategory, MenuItem, SaleTransaction } from "../types/models.js";

// Filtrar las ventas por locación
export function filterSalesByLocation(sales: SaleTransaction[], locationId: string): SaleTransaction[] {
	return sales.filter((sale) => sale.locationId === locationId);
}

// Filtrar las ventas por rango de fechas
export function filterSalesByDateRange(sales: SaleTransaction[], startDate: Date, endDate: Date): SaleTransaction[] {
	return sales.filter((sale) => sale.timestamp >= startDate && sale.timestamp <= endDate);
}

// Filtrar los ítems de menú por categoría
export function filterMenuItemsByCategory(items: MenuItem[], category: MenuCategory): MenuItem[] {
	return items.filter((item) => item.category === category);
}

// Filtro de locaciones activas
export function filterActiveLocations(locations: Location[]): Location[] {
    return locations.filter((location) => location.status === "Active");
}


// Funciones para ordenar datos de Brasaland

// Ordena las locaciones por capacidad de asientos
export function sortLocationsBySeatingCapacity(locations: Location[], order: "asc" | "desc"): Location[] {
  const sortedLocations = [...locations];

  if (order === "asc") {
    return sortedLocations.sort((a, b) => a.seatingCapacity - b.seatingCapacity);
  }

  return sortedLocations.sort((a, b) => b.seatingCapacity - a.seatingCapacity);
}

// Ordena los ítems del menú por precio en la moneda seleccionada (USD o COP)
// !!! PENDIENTE DE RESOLVER: PRECIO DISTINTO POR LOCACIÓN. POR AHORA SE USA EL PRECIO BASE !!!
export function sortMenuItemsByPrice(items: MenuItem[], currency: "USD" | "COP", order: "asc" | "desc"): MenuItem[] {
  const sortedItems = [...items];

  if (order === "asc") {
    return sortedItems.sort((a, b) => a.basePrice[currency] - b.basePrice[currency]);
  }

  return sortedItems.sort((a, b) => b.basePrice[currency] - a.basePrice[currency]);
}

