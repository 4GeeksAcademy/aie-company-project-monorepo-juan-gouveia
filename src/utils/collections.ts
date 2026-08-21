// Funciones para filtrar datos de Brasaland

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
    if (order === "asc") {
        return locations.sort((a, b) => a.seatingCapacity - b.seatingCapacity);
    }
    return locations.sort((a, b) => b.seatingCapacity - a.seatingCapacity);
}

