export function validateMenuItem(item: MenuItem): { valid: boolean, errors: string[] } {
  const errors: string[] = [];

  // Validar precios base en ambas monedas
  if (item.basePrice.USD <= 0) {
    errors.push("basePrice.USD debe ser mayor que 0");
  }

  if (item.basePrice.COP <= 0) {
    errors.push("basePrice.COP debe ser mayor que 0");
  }

  // Validar costo de ingredientes en ambas monedas
  if (item.ingredientCost.USD <= 0) {
    errors.push("ingredientCost.USD debe ser mayor que 0");
  }

  if (item.ingredientCost.COP <= 0) {
    errors.push("ingredientCost.COP debe ser mayor que 0");
  }

  // Validar tiempo de preparación
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