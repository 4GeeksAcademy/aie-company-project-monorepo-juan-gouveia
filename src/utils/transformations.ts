// Funciones para cálculos diversos en Brasaland

// Calcular el ingreso total diario en una fecha específica y en una moneda específica (USD o COP)
export function calculateDailyRevenue(sales: SaleTransaction[], date: Date, currency: "USD" | "COP"): number {
  const startOfDay = new Date(date);
  startOfDay.setHours(0, 0, 0, 0);

  const endOfDay = new Date(date);
  endOfDay.setHours(23, 59, 59, 999);

  const total = sales.filter((sale) => sale.timestamp >= startOfDay && sale.timestamp <= endOfDay).reduce((sum, sale) => sum + sale.totalPrice[currency], 0);

  return Math.round((total + Number.EPSILON) * 100) / 100;
}


// Calcular el margen de ganancia de una locación en un mes específico y en una moneda específica (USD o COP)
export function calculateLocationMargin(sales: SaleTransaction[], menuItems: MenuItem[], locationId: string, currency: "USD" | "COP"): number {

  const menuItemById = new Map(menuItems.map((item) => [item.id, item]));
  const locationSales = sales.filter((sale) => sale.locationId === locationId);
  const totalRevenue = locationSales.reduce((sum, sale) => sum + sale.totalPrice[currency], 0);
  const totalIngredientCost = locationSales.reduce((sum, sale) => {
    const menuItem = menuItemById.get(sale.itemId);
    if (!menuItem) {
      return sum;
    }

    const ingredientCostForSale = menuItem.ingredientCost[currency] * sale.quantity;

    return sum + ingredientCostForSale;
  }, 0);

  if (totalRevenue <= 0) {
    return 0;
  }

  const rawMargin = ((totalRevenue - totalIngredientCost) / totalRevenue) * 100;
  const clampedMargin = Math.min(100, Math.max(0, rawMargin));
  const roundedMargin = Math.round((clampedMargin + Number.EPSILON) * 100) / 100;

  return roundedMargin;
}


// Calcular el costo de desperdicio para una locación y en una moneda específica (USD o COP)
export function calculateWasteCost(wasteRecords: WasteRecord[], locationId: string, currency: "USD" | "COP"): number {
  const total = wasteRecords.filter((wasteRecord) => wasteRecord.locationId === locationId).reduce((sum, wasteRecord) => sum + wasteRecord.cost[currency], 0);

  return Math.round((total + Number.EPSILON) * 100) / 100;
}

// Hacer cambio de moneda entre USD y COP (tasa fija de 1 USD = 4000 COP)
export function convertCurrency(amount: number, fromCurrency: "USD" | "COP", toCurrency: "USD" | "COP"): number {
  if (fromCurrency === toCurrency) {
    return amount;
  }
  const converted =
    fromCurrency === "USD" ? amount * 4000 : amount / 4000;

  return Math.round((converted + Number.EPSILON) * 100) / 100;
}

