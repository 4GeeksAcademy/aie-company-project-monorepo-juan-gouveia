
// Función para validar ítems del menú
export function validateMenuItem(item: MenuItem): { valid: boolean, errors: string[] } {
  const errors: string[] = [];

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
export function validateSaleTransaction(sale: SaleTransaction): { valid: boolean, errors: string[] } {
  const errors: string[] = [];

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


