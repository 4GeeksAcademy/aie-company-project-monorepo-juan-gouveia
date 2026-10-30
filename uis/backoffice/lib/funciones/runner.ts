import {
  binarySearchLocationBySeatingCapacity,
  calculateAverageTicket,
  calculateCountryComparison,
  calculateDailyRevenue,
  calculateWasteCost,
  countSalesByPaymentMethod,
  filterActiveLocations,
  filterMenuItemsByCategory,
  filterSalesByDateRange,
  filterSalesByLocation,
  findLocationById,
  findMenuItemByName,
  findTopSellingItems,
  invalidLocation,
  invalidMenuItem,
  invalidSale,
  rankLocationsByPerformance,
  sampleLocations,
  sampleMenuItems,
  sampleSales,
  sampleWasteRecords,
  sortLocationsBySeatingCapacity,
  sortMenuItemsByPrice,
  validateLocation,
  validateMenuItem,
  validateSaleTransaction,
} from "@repo/brasa-core";
import type { MenuCategory } from "@repo/brasa-core";

export type Currency = "USD" | "COP";
export type Order = "asc" | "desc";
export type RunAction = (title: string, action: () => unknown) => void;

type FuncionesApi = {
  dataset: {
    sampleMenuItems: typeof sampleMenuItems;
    sampleSales: typeof sampleSales;
    sampleLocations: typeof sampleLocations;
    sampleWasteRecords: typeof sampleWasteRecords;
  };
  filters: {
    salesByLocation: (locationId: string) => typeof sampleSales;
    salesByDateRange: (startDateISO: string, endDateISO: string) => typeof sampleSales;
    menuByCategory: (category: MenuCategory) => typeof sampleMenuItems;
    activeLocations: () => typeof sampleLocations;
  };
  search: {
    locationById: (id: string) => ReturnType<typeof findLocationById>;
    menuItemByName: (name: string) => ReturnType<typeof findMenuItemByName>;
    locationCapacityBinary: (capacity: number) => number;
  };
  sort: {
    locationsByCapacity: (order: Order) => typeof sampleLocations;
    menuItemsByPrice: (currency: Currency, order: Order) => typeof sampleMenuItems;
  };
  reports: {
    dailyRevenue: (dateISO: string, currency: Currency) => number;
    averageTicket: (currency: Currency) => number;
    salesByPaymentMethod: () => ReturnType<typeof countSalesByPaymentMethod>;
    topSellingItems: (topN: number) => ReturnType<typeof findTopSellingItems>;
    wasteByLocation: (locationId: string, currency: Currency) => number;
    countryComparison: () => ReturnType<typeof calculateCountryComparison>;
    locationRanking: () => ReturnType<typeof rankLocationsByPerformance>;
  };
  validations: {
    menuItem: () => ReturnType<typeof validateMenuItem>;
    sale: () => ReturnType<typeof validateSaleTransaction>;
    location: () => ReturnType<typeof validateLocation>;
  };
};

const sortedLocationsAsc = (): typeof sampleLocations => sortLocationsBySeatingCapacity(sampleLocations, "asc");

export const funcionesApi: FuncionesApi = {
  dataset: {
    sampleMenuItems,
    sampleSales,
    sampleLocations,
    sampleWasteRecords,
  },
  filters: {
    salesByLocation: (locationId) => filterSalesByLocation(sampleSales, locationId),
    salesByDateRange: (startDateISO, endDateISO) => {
      const startDate = new Date(startDateISO);
      const endDate = new Date(endDateISO);
      return filterSalesByDateRange(sampleSales, startDate, endDate);
    },
    menuByCategory: (category) => filterMenuItemsByCategory(sampleMenuItems, category),
    activeLocations: () => filterActiveLocations(sampleLocations),
  },
  search: {
    locationById: (id) => findLocationById(sampleLocations, id),
    menuItemByName: (name) => findMenuItemByName(sampleMenuItems, name),
    locationCapacityBinary: (capacity) => binarySearchLocationBySeatingCapacity(sortedLocationsAsc(), capacity),
  },
  sort: {
    locationsByCapacity: (order) => sortLocationsBySeatingCapacity(sampleLocations, order),
    menuItemsByPrice: (currency, order) => sortMenuItemsByPrice(sampleMenuItems, currency, order),
  },
  reports: {
    dailyRevenue: (dateISO, currency) => calculateDailyRevenue(sampleSales, new Date(dateISO), currency),
    averageTicket: (currency) => calculateAverageTicket(sampleSales, currency),
    salesByPaymentMethod: () => countSalesByPaymentMethod(sampleSales),
    topSellingItems: (topN) => findTopSellingItems(sampleSales, sampleMenuItems, topN),
    wasteByLocation: (locationId, currency) => calculateWasteCost(sampleWasteRecords, locationId, currency),
    countryComparison: () => calculateCountryComparison(sampleSales, sampleLocations, sampleMenuItems),
    locationRanking: () => rankLocationsByPerformance(sampleLocations, sampleSales, sampleWasteRecords, sampleMenuItems),
  },
  validations: {
    menuItem: () => validateMenuItem(invalidMenuItem),
    sale: () => validateSaleTransaction(invalidSale),
    location: () => validateLocation(invalidLocation),
  },
};
