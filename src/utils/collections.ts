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

