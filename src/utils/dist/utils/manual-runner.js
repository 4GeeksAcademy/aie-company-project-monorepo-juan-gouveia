import { filterActiveLocations, filterMenuItemsByCategory, filterSalesByDateRange, filterSalesByLocation, sortLocationsBySeatingCapacity, sortMenuItemsByPrice } from "./collections.js";
import { binarySearchLocationBySeatingCapacity, findLocationById, findMenuItemByName } from "./search.js";
import { calculateAverageTicket, calculateCountryComparison, calculateDailyRevenue, calculateWasteCost, countSalesByPaymentMethod, findTopSellingItems, rankLocationsByPerformance } from "./transformations.js";
import { validateLocation, validateMenuItem, validateSaleTransaction } from "./validations.js";
import { invalidLocation, invalidMenuItem, invalidSale, sampleLocations, sampleMenuItems, sampleSales, sampleWasteRecords } from "./test-data.js";
const sortedLocationsAsc = () => sortLocationsBySeatingCapacity(sampleLocations, "asc");
const api = {
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
window.brasaManual = api;
export { api as brasaManualApi };
