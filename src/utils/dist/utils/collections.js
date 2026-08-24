// Funciones para filtrar datos de Brasaland
// Filtrar las ventas por locación
export function filterSalesByLocation(sales, locationId) {
    return sales.filter((sale) => sale.locationId === locationId);
}
// Filtrar las ventas por rango de fechas
export function filterSalesByDateRange(sales, startDate, endDate) {
    return sales.filter((sale) => sale.timestamp >= startDate && sale.timestamp <= endDate);
}
// Filtrar los ítems de menú por categoría
export function filterMenuItemsByCategory(items, category) {
    return items.filter((item) => item.category === category);
}
// Filtro de locaciones activas
export function filterActiveLocations(locations) {
    return locations.filter((location) => location.status === "Active");
}
// Funciones para ordenar datos de Brasaland
// Ordena las locaciones por capacidad de asientos
export function sortLocationsBySeatingCapacity(locations, order) {
    const sortedLocations = [...locations];
    if (order === "asc") {
        return sortedLocations.sort((a, b) => a.seatingCapacity - b.seatingCapacity);
    }
    return sortedLocations.sort((a, b) => b.seatingCapacity - a.seatingCapacity);
}
// Ordena los ítems del menú por precio en la moneda seleccionada (USD o COP)
// !!! PENDIENTE DE RESOLVER: PRECIO DISTINTO POR LOCACIÓN. POR AHORA SE USA EL PRECIO BASE !!!
export function sortMenuItemsByPrice(items, currency, order) {
    const sortedItems = [...items];
    if (order === "asc") {
        return sortedItems.sort((a, b) => a.basePrice[currency] - b.basePrice[currency]);
    }
    return sortedItems.sort((a, b) => b.basePrice[currency] - a.basePrice[currency]);
}
