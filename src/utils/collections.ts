export function filterSalesByLocation(sales: SaleTransaction[], locationId: string): SaleTransaction[] {
	return sales.filter((sale) => sale.locationId === locationId);
}

export function filterSalesByDateRange(sales: SaleTransaction[], startDate: Date, endDate: Date): SaleTransaction[] {
	return sales.filter((sale) => sale.timestamp >= startDate && sale.timestamp <= endDate);
}

