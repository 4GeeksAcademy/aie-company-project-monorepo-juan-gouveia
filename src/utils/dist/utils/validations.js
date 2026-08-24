export function validateMenuItem(item) {
    const errors = [];
    // Validar basePrice en ambas monedas
    if (item.basePrice.USD <= 0) {
        errors.push("basePrice.USD debe ser mayor que 0");
    }
    if (item.basePrice.COP <= 0) {
        errors.push("basePrice.COP debe ser mayor que 0");
    }
    // Validar ingredientCost en ambas monedas
    if (item.ingredientCost.USD <= 0) {
        errors.push("ingredientCost.USD debe ser mayor que 0");
    }
    if (item.ingredientCost.COP <= 0) {
        errors.push("ingredientCost.COP debe ser mayor que 0");
    }
    // Validar prepTimeMinutes
    if (item.prepTimeMinutes <= 0) {
        errors.push("prepTimeMinutes debe ser mayor que 0");
    }
    if (item.prepTimeMinutes > 60) {
        errors.push("prepTimeMinutes debe ser menor o igual a 60");
    }
    // Validar nombre no vacío
    if (item.name.trim().length === 0) {
        errors.push("name no debe estar vacío");
    }
    // Validar disponibilidad en al menos un país
    if (!item.isAvailableInColombia && !item.isAvailableInUSA) {
        errors.push("El ítem debe estar disponible en al menos un país");
    }
    return {
        valid: errors.length === 0,
        errors,
    };
}
// Función para validar ventas
export function validateSaleTransaction(sale) {
    const errors = [];
    // Validar quantity
    if (sale.quantity <= 0) {
        errors.push("quantity debe ser mayor que 0");
    }
    // Validar totalPrice en ambas monedas
    if (sale.totalPrice.USD <= 0) {
        errors.push("totalPrice.USD debe ser mayor que 0");
    }
    if (sale.totalPrice.COP <= 0) {
        errors.push("totalPrice.COP debe ser mayor que 0");
    }
    // Validar waiterName no vacío
    if (sale.waiterName.trim().length === 0) {
        errors.push("waiterName no debe estar vacío");
    }
    return {
        valid: errors.length === 0,
        errors,
    };
}
// Función para validar locaciones
export function validateLocation(location) {
    const errors = [];
    const currentYear = new Date().getFullYear();
    // Validar openingYear
    if (location.openingYear < 2008) {
        errors.push("openingYear debe ser mayor o igual a 2008");
    }
    if (location.openingYear > currentYear) {
        errors.push("openingYear debe ser menor o igual al año actual");
    }
    // Validar seatingCapacity
    if (location.seatingCapacity <= 0) {
        errors.push("seatingCapacity debe ser mayor que 0");
    }
    // Validar staffCount
    if (location.staffCount <= 0) {
        errors.push("staffCount debe ser mayor que 0");
    }
    // Validar monthlyRentCost en ambas monedas
    if (location.monthlyRentCost.USD <= 0) {
        errors.push("monthlyRentCost.USD debe ser mayor que 0");
    }
    if (location.monthlyRentCost.COP <= 0) {
        errors.push("monthlyRentCost.COP debe ser mayor que 0");
    }
    // Validar averageMonthlyUtilities en ambas monedas
    if (location.averageMonthlyUtilities.USD <= 0) {
        errors.push("averageMonthlyUtilities.USD debe ser mayor que 0");
    }
    if (location.averageMonthlyUtilities.COP <= 0) {
        errors.push("averageMonthlyUtilities.COP debe ser mayor que 0");
    }
    return {
        valid: errors.length === 0,
        errors,
    };
}
