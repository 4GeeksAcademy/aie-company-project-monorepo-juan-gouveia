import type { Location, MenuItem, SaleTransaction, WasteRecord } from "../types/models.js";

// Ítems de Menú de Ejemplo
export const sampleMenuItems: MenuItem[] = [
  {
    id: "ITEM-PICANHA-250",
    name: "Picanha 250g",
    category: "Meat",
    basePrice: { USD: 18.5, COP: 74000 },
    ingredientCost: { USD: 7.2, COP: 28800 },
    prepTimeMinutes: 15,
    isAvailableInColombia: true,
    isAvailableInUSA: true,
    allergens: [],
    status: "Active",
  },
  {
    id: "ITEM-FRIES",
    name: "Papas Fritas",
    category: "Side",
    basePrice: { USD: 4.5, COP: 18000 },
    ingredientCost: { USD: 1.2, COP: 4800 },
    prepTimeMinutes: 8,
    isAvailableInColombia: true,
    isAvailableInUSA: true,
    allergens: [],
    status: "Active",
  },
  {
    id: "ITEM-COKE",
    name: "Coca-Cola",
    category: "Beverage",
    basePrice: { USD: 2.5, COP: 10000 },
    ingredientCost: { USD: 0.8, COP: 3200 },
    prepTimeMinutes: 2,
    isAvailableInColombia: true,
    isAvailableInUSA: true,
    allergens: [],
    status: "Active",
  },
];

// Locaciones de Ejemplo
export const sampleLocations: Location[] = [
  {
    id: "LOC-MEDELLIN-01",
    name: "Brasaland Medellín Centro",
    city: "Medellín",
    country: "Colombia",
    openingYear: 2008,
    seatingCapacity: 80,
    staffCount: 12,
    monthlyRentCost: { USD: 1500, COP: 6000000 },
    averageMonthlyUtilities: { USD: 400, COP: 1600000 },
    manager: "Carlos Jiménez",
    status: "Active",
  },
  {
    id: "LOC-MIAMI-01",
    name: "Brasaland Miami Beach",
    city: "Miami",
    country: "USA",
    openingYear: 2018,
    seatingCapacity: 100,
    staffCount: 15,
    monthlyRentCost: { USD: 5500, COP: 22000000 },
    averageMonthlyUtilities: { USD: 800, COP: 3200000 },
    manager: "Jake Morrison",
    status: "Active",
  },
];


// Ventas de Ejemplo
export const sampleSales: SaleTransaction[] = [
  {
    id: "TXN-2024-15482",
    locationId: "LOC-MEDELLIN-01",
    itemId: "ITEM-PICANHA-250",
    quantity: 2,
    totalPrice: { USD: 37.0, COP: 148000 },
    paymentMethod: "Credit card",
    timestamp: new Date("2024-03-15T19:30:00"),
    waiterName: "María González",
  },
  {
    id: "TXN-2024-15483",
    locationId: "LOC-MIAMI-01",
    itemId: "ITEM-FRIES",
    quantity: 3,
    totalPrice: { USD: 13.5, COP: 54000 },
    paymentMethod: "Cash",
    timestamp: new Date("2024-03-15T20:15:00"),
    waiterName: "John Smith",
  },
];


// Registros de desperdicio de ejemplo
export const sampleWasteRecords: WasteRecord[] = [
  {
    id: "WST-2024-2001",
    locationId: "LOC-MEDELLIN-01",
    itemId: "ITEM-FRIES",
    quantity: 1,
    reason: "Expired",
    cost: { USD: 1.2, COP: 4800 },
    timestamp: new Date("2024-03-15T22:00:00"),
    reportedBy: "Ana López",
  },
  {
    id: "WST-2024-2002",
    locationId: "LOC-MIAMI-01",
    itemId: "ITEM-COKE",
    quantity: 2,
    reason: "Damage",
    cost: { USD: 1.6, COP: 6400 },
    timestamp: new Date("2024-03-16T10:00:00"),
    reportedBy: "Mike Brown",
  },
];


// Casos inválidos para pruebas de validación
export const invalidMenuItem: MenuItem = {
  id: "ITEM-INVALID",
  name: "   ",
  category: "Meat",
  basePrice: { USD: 0, COP: -1000 },
  ingredientCost: { USD: 0, COP: -500 },
  prepTimeMinutes: 0,
  isAvailableInColombia: false,
  isAvailableInUSA: false,
  allergens: [],
  status: "Active",
};


export const invalidSale: SaleTransaction = {
  id: "TXN-INVALID-01",
  locationId: "LOC-MEDELLIN-01",
  itemId: "ITEM-PICANHA-250",
  quantity: 0,
  totalPrice: { USD: -10, COP: 0 },
  paymentMethod: "Cash",
  timestamp: new Date("2024-03-15T21:30:00"),
  waiterName: "   ",
};


export const invalidLocation: Location = {
  id: "LOC-INVALID-01",
  name: "Locación Inválida",
  city: "Bogotá",
  country: "Colombia",
  openingYear: 2007,
  seatingCapacity: 0,
  staffCount: 0,
  monthlyRentCost: { USD: 0, COP: -100 },
  averageMonthlyUtilities: { USD: 0, COP: -100 },
  manager: "N/A",
  status: "Active",
};