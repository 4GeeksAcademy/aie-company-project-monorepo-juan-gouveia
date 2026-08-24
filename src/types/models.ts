// Interfaces y tipos para el proyecto de Brasaland

// Interfaz para ítem del menú (MenuItem) de Brasaland:
// Reglas de validación:
    // Ambos precios USD y COP deben ser > 0
    // prepTimeMinutes debe ser > 0 y <= 60
    // name no debe estar vacío
    // El ítem debe estar disponible en al menos un país

export interface MenuItem {
  id: string; // ID del ítem (ej: "ITEM-PICANHA-250")
  name: string; // Nombre del ítem (ej: "Picanha 250g")
  category: MenuCategory; // Categoría de comida
  basePrice: Price; // Precio base (puede variar por locación)
  ingredientCost: Price; // Costo de ingredientes por unidad
  prepTimeMinutes: number; // Tiempo promedio de preparación
  isAvailableInColombia: boolean;
  isAvailableInUSA: boolean;
  allergens: string[]; // Lista de alérgenos
  status: MenuItemStatus;
}

export interface Price {
  USD: number; // Precio en Dólares Estadounidenses
  COP: number; // Precio en Pesos Colombianos
}

export type MenuCategory = "Meat" | "Side" | "Beverage" | "Dessert" | "Combo";
export type MenuItemStatus = "Active" | "Seasonal" | "Discontinued";

// --------------------------------------------------------

// Interfaz para una venta (SaleTransaction) de Brasaland
// Reglas de validación:
    // quantity debe ser > 0
    // Ambos valores de precio deben ser > 0
    // waiterName no debe estar vacío

export interface SaleTransaction {
  id: string; // ID de transacción (ej: "TXN-2024-15482")
  locationId: string; // Locación donde ocurrió la venta
  itemId: string; // Ítem de menú vendido
  quantity: number; // Número de unidades vendidas
  totalPrice: Price; // Precio total cobrado
  paymentMethod: PaymentMethod; // Cómo pagó el cliente
  timestamp: Date; // Cuándo ocurrió la venta
  waiterName: string; // Miembro del personal que atendió
}

export type PaymentMethod = "Cash" | "Credit card" | "Debit card" | "Digital wallet";

// --------------------------------------------------------

// Interfaz para una locación (Location) de Brasaland
// Reglas de validación:
    // openingYear debe ser >= 2008 y <= año actual
    // seatingCapacity debe ser > 0
    // staffCount debe ser > 0
    // Ambos costos de renta y servicios deben ser > 0

export interface Location {
  id: string; // ID de locación (ej: "LOC-MEDELLIN-01")
  name: string; // Nombre de la locación
  city: string; // Nombre de la ciudad
  country: Country; // Colombia o USA
  openingYear: number; // Año de apertura
  seatingCapacity: number; // Número máximo de clientes
  staffCount: number; // Número de empleados
  monthlyRentCost: Price; // Renta mensual
  averageMonthlyUtilities: Price; // Servicios mensuales promedio
  manager: string; // Nombre del gerente de locación
  status: LocationStatus;
}

export type Country = "Colombia" | "USA";
export type LocationStatus = "Active" | "Temporarily closed" | "Under renovation";

// --------------------------------------------------------

// Interfaz para registro de desperdicio (WasteRecord) de Brasaland
// Reglas de validación:
    // No se recibieron reglas de validación específicas para WasteRecord, pero se asume que:
        // locationId debe ser válido y existente
        // itemId debe ser válido y existente
        // quantity debe ser > 0
        // reason no debe estar vacío
        // timestamp debe ser una fecha válida
        // reportedBy no debe estar vacío
        // cost debe ser > 0

export interface WasteRecord {
  id: string; // ID de registro de desperdicio
  locationId: string; // Locación donde ocurrió el desperdicio
  itemId: string; // Ítem de menú desperdiciado
  quantity: number; // Número de unidades desperdiciadas
  reason: WasteReason; // Por qué se desperdició
  cost: Price; // Costo de ítems desperdiciados
  timestamp: Date; // Cuándo se registró
  reportedBy: string; // Miembro del personal que lo reportó
}

export type WasteReason =
  | "Expired"
  | "Cooking error"
  | "Customer return"
  | "Damage"
  | "Other";

// --------------------------------------------------------

// Interfaz para métricas de país (CountryMetrics) de Brasaland
// Reglas de validación:
    // No se recibieron reglas de validación específicas para CountryMetrics, pero se asume que:
        // Todos los valores numéricos deben ser >= 0

export interface CountryMetrics {
  totalLocations: number;
  totalRevenue: Price;
  averageRevenuePerLocation: Price;
  totalSales: number;
}

// --------------------------------------------------------

