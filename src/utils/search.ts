// Funciones para operaciones de búsqueda en Brasaland

// Buscar una locación por su ID
export function findLocationById(locations: Location[], id: string): Location | null {
  return locations.find((location) => location.id === id) || null;
}

// Buscar ítem del menú por su nombre (case-insensitive)
export function findMenuItemByName(items: MenuItem[], name: string): MenuItem | null {
  const lowerCaseName = name.toLowerCase();
  return items.find((item) => item.name.toLowerCase() === lowerCaseName) || null;
}

// Búsqueda binaria en un array de locaciones que supone ordenadas (ascendente) por capacidad para retornar el índice de una locación con la capacidad objetivo (retorna -1 si no lo encuentra)
export function binarySearchLocationBySeatingCapacity(sortedLocations: Location[], targetCapacity: number): number {
  let left = 0;
  let right = sortedLocations.length - 1;

  while (left <= right) {
    const mid = Math.floor((left + right) / 2);
    const midCapacity = sortedLocations[mid].seatingCapacity;

    if (midCapacity === targetCapacity) {
      return mid;
    }
    // Locación encontrada con éxito

    if (midCapacity < targetCapacity) {
      left = mid + 1;
    } else {
      right = mid - 1;
    }
  }

  return -1;
  // Locación no encontrada
}