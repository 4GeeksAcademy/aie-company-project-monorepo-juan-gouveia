// ARCHIVO GENERADO por scripts/generate-telemetry-catalog.mjs desde docs/telemetry/event-schemas.json.
// No lo edites a mano: cambia el esquema y ejecuta `npm run telemetry:catalog`.
//
// Eventos que emite el backoffice (source: "browser"), con la versión de su esquema, sus propiedades
// obligatorias y su allowlist.

export interface CatalogEntry {
  version: string;
  required: readonly string[];
  allowed: readonly string[];
}

export const TELEMETRY_CATALOG: Readonly<Record<string, CatalogEntry>> = {
  "inbound_order_created": {
    "version": "1.0.0",
    "required": [
      "order_id",
      "location_id",
      "country",
      "product_id",
      "product_category",
      "quantity",
      "unit",
      "currency",
      "supplier_id",
      "unit_cost"
    ],
    "allowed": [
      "order_id",
      "location_id",
      "country",
      "product_id",
      "product_category",
      "quantity",
      "unit",
      "currency",
      "supplier_id",
      "unit_cost"
    ]
  },
  "outbound_order_created": {
    "version": "1.0.0",
    "required": [
      "order_id",
      "location_id",
      "country",
      "product_id",
      "product_category",
      "quantity",
      "unit",
      "currency"
    ],
    "allowed": [
      "order_id",
      "location_id",
      "country",
      "product_id",
      "product_category",
      "quantity",
      "unit",
      "currency",
      "stock_after"
    ]
  },
  "stock_waste_registered": {
    "version": "1.1.0",
    "required": [
      "order_id",
      "location_id",
      "country",
      "product_id",
      "product_category",
      "quantity",
      "unit",
      "currency",
      "reason"
    ],
    "allowed": [
      "order_id",
      "location_id",
      "country",
      "product_id",
      "product_category",
      "quantity",
      "unit",
      "currency",
      "reason",
      "unit_cost",
      "stock_after"
    ]
  },
  "stock_threshold_triggered": {
    "version": "1.0.0",
    "required": [
      "location_id",
      "country",
      "product_id",
      "product_category",
      "quantity",
      "unit",
      "currency",
      "threshold_quantity",
      "trigger_order_id"
    ],
    "allowed": [
      "location_id",
      "country",
      "product_id",
      "product_category",
      "quantity",
      "unit",
      "currency",
      "threshold_quantity",
      "trigger_order_id"
    ]
  },
  "direct_stock_edit_rejected": {
    "version": "1.0.0",
    "required": [
      "method",
      "route",
      "rejection_type",
      "status_code",
      "user_role"
    ],
    "allowed": [
      "location_id",
      "country",
      "product_id",
      "product_category",
      "quantity",
      "unit",
      "currency",
      "method",
      "route",
      "rejection_type",
      "status_code",
      "user_role"
    ]
  },
  "ingredient_price_variance_detected": {
    "version": "1.0.0",
    "required": [
      "order_id",
      "location_id",
      "country",
      "product_id",
      "product_category",
      "quantity",
      "unit",
      "currency",
      "supplier_id",
      "unit_cost",
      "historical_avg_unit_cost",
      "variance_pct",
      "threshold_pct",
      "history_window_days",
      "history_sample_size"
    ],
    "allowed": [
      "order_id",
      "location_id",
      "country",
      "product_id",
      "product_category",
      "quantity",
      "unit",
      "currency",
      "supplier_id",
      "unit_cost",
      "historical_avg_unit_cost",
      "variance_pct",
      "threshold_pct",
      "history_window_days",
      "history_sample_size"
    ]
  },
  "order_validation_failed": {
    "version": "1.0.0",
    "required": [
      "order_type",
      "error_code",
      "invalid_fields",
      "status_code"
    ],
    "allowed": [
      "order_type",
      "product_id",
      "location_id",
      "error_code",
      "invalid_fields",
      "status_code"
    ]
  },
  "outbound_order_rejected": {
    "version": "1.0.0",
    "required": [
      "location_id",
      "country",
      "product_id",
      "product_category",
      "quantity",
      "unit",
      "currency",
      "available_quantity",
      "outbound_type"
    ],
    "allowed": [
      "location_id",
      "country",
      "product_id",
      "product_category",
      "quantity",
      "unit",
      "currency",
      "available_quantity",
      "outbound_type"
    ]
  },
  "login_succeeded": {
    "version": "1.0.0",
    "required": [
      "user_role"
    ],
    "allowed": [
      "user_role"
    ]
  },
  "login_failed": {
    "version": "2.0.0",
    "required": [
      "failure_reason"
    ],
    "allowed": [
      "failure_reason"
    ]
  },
  "session_expired": {
    "version": "1.0.0",
    "required": [
      "route",
      "token_age_minutes"
    ],
    "allowed": [
      "route",
      "token_age_minutes"
    ]
  },
  "auth_token_rejected": {
    "version": "1.0.0",
    "required": [
      "rejection_reason",
      "route"
    ],
    "allowed": [
      "rejection_reason",
      "route"
    ]
  },
  "logout_completed": {
    "version": "1.0.0",
    "required": [
      "route",
      "session_duration_seconds"
    ],
    "allowed": [
      "route",
      "session_duration_seconds"
    ]
  },
  "user_registered": {
    "version": "1.0.0",
    "required": [
      "new_user_id",
      "user_role"
    ],
    "allowed": [
      "new_user_id",
      "user_role"
    ]
  },
  "password_reset_completed": {
    "version": "1.0.0",
    "required": [
      "link_age_minutes"
    ],
    "allowed": [
      "link_age_minutes"
    ]
  },
  "password_reset_link_rejected": {
    "version": "1.0.0",
    "required": [
      "rejection_reason",
      "stage"
    ],
    "allowed": [
      "rejection_reason",
      "stage"
    ]
  },
  "password_changed": {
    "version": "1.0.0",
    "required": [
      "channel"
    ],
    "allowed": [
      "days_since_last_change",
      "channel"
    ]
  },
  "page_viewed": {
    "version": "1.0.0",
    "required": [
      "route",
      "navigation_type"
    ],
    "allowed": [
      "route",
      "previous_route",
      "navigation_type",
      "user_role"
    ]
  },
  "form_validation_failed": {
    "version": "1.0.0",
    "required": [
      "form_id",
      "invalid_fields",
      "error_count"
    ],
    "allowed": [
      "form_id",
      "invalid_fields",
      "error_count"
    ]
  },
  "form_abandoned": {
    "version": "1.0.0",
    "required": [
      "form_id",
      "last_field",
      "filled_field_count",
      "time_in_form_seconds",
      "exit"
    ],
    "allowed": [
      "form_id",
      "last_field",
      "filled_field_count",
      "time_in_form_seconds",
      "exit"
    ]
  },
  "list_filter_applied": {
    "version": "1.0.0",
    "required": [
      "list_id",
      "filter_name",
      "result_count"
    ],
    "allowed": [
      "list_id",
      "filter_name",
      "filter_value",
      "query_length",
      "result_count"
    ]
  },
  "list_page_extended": {
    "version": "1.0.0",
    "required": [
      "list_id",
      "visible_rows",
      "total_rows",
      "filters_active"
    ],
    "allowed": [
      "list_id",
      "visible_rows",
      "total_rows",
      "filters_active"
    ]
  },
  "api_latency_recorded": {
    "version": "1.0.0",
    "required": [
      "method",
      "route",
      "status_code",
      "duration_ms",
      "sample_rate"
    ],
    "allowed": [
      "method",
      "route",
      "status_code",
      "duration_ms",
      "cache",
      "sample_rate"
    ]
  },
  "page_performance_recorded": {
    "version": "1.0.0",
    "required": [
      "route",
      "device_class"
    ],
    "allowed": [
      "route",
      "lcp_ms",
      "cls",
      "inp_ms",
      "data_ready_ms",
      "device_class",
      "effective_connection"
    ]
  },
  "api_error_returned": {
    "version": "1.0.0",
    "required": [
      "method",
      "route",
      "status_code",
      "error_code"
    ],
    "allowed": [
      "method",
      "route",
      "status_code",
      "error_code"
    ]
  },
  "frontend_error_captured": {
    "version": "1.0.0",
    "required": [
      "route",
      "error_name",
      "message_sanitized",
      "error_fingerprint",
      "source"
    ],
    "allowed": [
      "route",
      "error_name",
      "message_sanitized",
      "error_fingerprint",
      "source"
    ]
  },
  "api_connection_failed": {
    "version": "1.1.0",
    "required": [
      "method",
      "route",
      "failure",
      "status_code",
      "duration_ms"
    ],
    "allowed": [
      "method",
      "route",
      "failure",
      "status_code",
      "duration_ms"
    ]
  },
  "supplier_created": {
    "version": "1.0.0",
    "required": [
      "supplier_id",
      "country",
      "categories",
      "currency",
      "status"
    ],
    "allowed": [
      "supplier_id",
      "country",
      "categories",
      "currency",
      "status"
    ]
  },
  "supplier_rate_updated": {
    "version": "1.0.0",
    "required": [
      "supplier_id",
      "country",
      "currency",
      "previous_rate",
      "new_rate",
      "change_pct"
    ],
    "allowed": [
      "supplier_id",
      "country",
      "currency",
      "previous_rate",
      "new_rate",
      "change_pct"
    ]
  },
  "supplier_status_changed": {
    "version": "1.0.0",
    "required": [
      "supplier_id",
      "country",
      "categories",
      "previous_status",
      "new_status"
    ],
    "allowed": [
      "supplier_id",
      "country",
      "categories",
      "previous_status",
      "new_status"
    ]
  },
  "incident_created": {
    "version": "1.0.0",
    "required": [
      "incident_id",
      "category",
      "origin",
      "branch",
      "status"
    ],
    "allowed": [
      "incident_id",
      "category",
      "origin",
      "branch",
      "status"
    ]
  },
  "incident_status_changed": {
    "version": "1.0.0",
    "required": [
      "incident_id",
      "category",
      "branch",
      "previous_status",
      "new_status",
      "minutes_since_created",
      "minutes_in_previous_status"
    ],
    "allowed": [
      "incident_id",
      "category",
      "branch",
      "previous_status",
      "new_status",
      "minutes_since_created",
      "minutes_in_previous_status"
    ]
  },
  "incident_transition_rejected": {
    "version": "1.0.0",
    "required": [
      "incident_id",
      "current_status",
      "requested_status"
    ],
    "allowed": [
      "incident_id",
      "current_status",
      "requested_status"
    ]
  },
  "incident_report_analyzed": {
    "version": "1.0.0",
    "required": [
      "total_rows",
      "valid_rows",
      "invalid_rows",
      "invalid_by_rule",
      "file_size_bytes"
    ],
    "allowed": [
      "total_rows",
      "valid_rows",
      "invalid_rows",
      "invalid_by_rule",
      "file_size_bytes"
    ]
  }
};
