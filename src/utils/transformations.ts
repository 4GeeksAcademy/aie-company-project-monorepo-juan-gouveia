// Funciones para cálculos financieros en Brasaland

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


// Funciones para puntuar el performance de las locaciones de Brasaland

//Función para puntuar el performance de una locación basada en ingresos, eficiencia, desperdicio y margen de ganancia
export function scoreLocationPerformance(location: Location, sales: SaleTransaction[], wasteRecords: WasteRecord[], menuItems: MenuItem[]): number {
  const locationCurrency: "USD" | "COP" = location.country === "Colombia" ? "COP" : "USD";
  const locationSales = sales.filter((sale) => sale.locationId === location.id);
  const totalRevenue = locationSales.reduce((sum, sale) => sum + sale.totalPrice[locationCurrency], 0);

  const operatingStartDate = new Date(location.openingYear, 0, 1);
  const now = new Date();
  const millisecondsPerDay = 1000 * 60 * 60 * 24;
  const operatingDays = Math.max(1, Math.floor((now.getTime() - operatingStartDate.getTime()) / millisecondsPerDay) + 1);

  const averageDailyRevenue = totalRevenue / operatingDays;
  const revenueBenchmark = locationCurrency === "USD" ? 1000 : convertCurrency(1000, "USD", "COP");
  const revenueScore = Math.min((averageDailyRevenue / revenueBenchmark) * 40, 40);

  const efficiencyScore = Math.min((locationSales.length / location.seatingCapacity) * 30, 30);

  const totalWasteCost = wasteRecords.filter((wasteRecord) => wasteRecord.locationId === location.id).reduce((sum, wasteRecord) => sum + wasteRecord.cost[locationCurrency], 0);

  const wastePercentage = totalRevenue > 0 ? (totalWasteCost / totalRevenue) * 100 : 100;
  const wasteScore = Math.max(20 - wastePercentage * 2, 0);

  const margin = calculateLocationMargin(locationSales, menuItems, location.id, locationCurrency);
  const marginScore = Math.min(margin / 10, 10);

  const rawTotalScore = revenueScore + efficiencyScore + wasteScore + marginScore;
  const boundedTotalScore = Math.min(100, Math.max(0, rawTotalScore));

  return Math.round((boundedTotalScore + Number.EPSILON) * 100) / 100;
}

// Función para obtener un ranking de locaciones basado en su puntaje de performance (reutilizando la función scoreLocationPerformance)
export function rankLocationsByPerformance(locations: Location[], sales: SaleTransaction[], wasteRecords: WasteRecord[], menuItems: MenuItem[]): Array<{ location: Location, score: number }> {
  return locations.map((location) => ({location, score: scoreLocationPerformance(location, sales, wasteRecords, menuItems),})).sort((a, b) => b.score - a.score);
}