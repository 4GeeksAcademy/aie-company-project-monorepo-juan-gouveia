// Inventario (Hito 5): tipos con los nombres de entidades y campos del briefing, tal como los
// devuelve la API (/api/v1/inventory). `current_stock` es calculado por la API: nunca se envía.

export type Unit = "kg" | "litro" | "unidad";
export type Category = "meat" | "produce" | "sauce" | "beverage" | "packaging" | "cleaning";
export type Country = "CO" | "US";
export type ExitReason = "consumption" | "waste";
// Motivo de una merma (brecha B6 del plan de telemetría), con los valores del briefing.
export type WasteReason = "expired" | "kitchen_error" | "theft_suspected";

// `Ingredient` con su stock calculado (entradas − salidas).
export interface Ingredient {
  id: number;
  name: string;
  sku: string;
  unit: Unit;
  category: Category;
  country: Country;
  current_stock: number;
}

// Cada orden lleva una proyección plana de su ingrediente (id, nombre, SKU y unidad), sin objeto
// anidado (docs/serialization-audit.md, decisión D4).
interface OrderBase {
  id: number;
  ingredient_id: number;
  ingredient_name: string;
  ingredient_sku: string;
  ingredient_unit: Unit;
  quantity: number;
  location_id: number;
  // ISO 8601 en UTC.
  created_at: string;
  // UUID (TinyDB) del usuario que registró la orden; lo pone la API a partir del token.
  user_uuid: string;
}

// Orden de entrada: entrega de un proveedor.
export interface IngredientEntry extends OrderBase {
  supplier_name: string;
  // Coste por unidad en la moneda del país del ingrediente (COP o USD); null en entradas anteriores
  // a la brecha B5.
  unit_cost: number | null;
}

// Orden de salida: consumo o merma.
export interface IngredientExit extends OrderBase {
  reason: ExitReason;
  // Solo en las mermas; null en los consumos y en mermas anteriores a la brecha B6.
  waste_reason: WasteReason | null;
}

// Respuesta de GET /inventory/orders: cada lista de la más reciente a la más antigua.
export interface OrdersResponse {
  inbound: IngredientEntry[];
  outbound: IngredientExit[];
}

// Cuerpo de POST /inventory/orders/inbound. La API no admite `user_uuid` ni `created_at`.
export interface IngredientEntryInput {
  ingredient_id: number;
  quantity: number;
  supplier_name: string;
  unit_cost: number;
  location_id: number;
}

// Cuerpo de POST /inventory/orders/outbound. `waste_reason` es obligatorio en las mermas y no se
// envía en los consumos.
export interface IngredientExitInput {
  ingredient_id: number;
  quantity: number;
  reason: ExitReason;
  waste_reason?: WasteReason;
  location_id: number;
}
