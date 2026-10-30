import type { Currency, Order } from "@/lib/funciones/runner";

export const CURRENCY_OPTIONS: Record<Currency, string> = { USD: "USD", COP: "COP" };

export const ORDER_OPTIONS: Record<Order, string> = { asc: "asc", desc: "desc" };
