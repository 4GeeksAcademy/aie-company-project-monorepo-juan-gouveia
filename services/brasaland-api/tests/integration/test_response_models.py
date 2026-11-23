"""Guarda de la auditoría de serialización (docs/serialization-audit.md, subfase 2d).

Recorre el esquema OpenAPI de la app real (el contrato que ven los clientes) y falla si una ruta nueva o modificada rompe
los criterios de la auditoría:

- toda respuesta JSON es un modelo Pydantic con nombre (o una lista de ellos), no un `dict` ni un
  esquema genérico, salvo las excepciones con nombre;
- ninguna respuesta expone contraseñas, hashes ni tokens de restablecimiento;
- las rutas de auth que no son `GET /auth/me` no devuelven el email;
- ninguna escritura reutiliza su esquema de salida como esquema de entrada.
"""

# Única ruta sin esquema Pydantic: devuelve el archivo results.csv, no JSON. Declara
# `response_model=None` a propósito (auditoría, I2; BRIEFING_DIVERGENCES.md, sección 13).
ROUTES_WITHOUT_RESPONSE_MODEL = {("GET", "/api/v1/incidents/results/export")}

# Campos que no pueden aparecer en ninguna respuesta. `access_token` sí: es lo que piden el login
# y el cambio de contraseña.
SENSITIVE_FIELDS = {"password", "hashed_password", "password_changed_at", "current_password", "new_password", "token"}

# Flujos de auth que no deben reenviar el email. `GET /auth/me` queda fuera: devuelve el del propio
# usuario autenticado, y la vista de cuenta depende de ello.
AUTH_ROUTES_WITHOUT_EMAIL = {
    ("POST", "/api/v1/users"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/forgot-password"),
    ("POST", "/api/v1/auth/reset-password/validate"),
    ("POST", "/api/v1/auth/reset-password"),
    ("POST", "/api/v1/auth/change-password"),
}

WRITE_METHODS = {"post", "put", "patch"}


def success_response(operation: dict) -> dict:
    return next(response for code, response in operation["responses"].items() if code.startswith("2"))


def success_schema(operation: dict) -> dict | None:
    """Esquema JSON de la respuesta 2xx de una operación OpenAPI, o None si no responde JSON."""
    return success_response(operation).get("content", {}).get("application/json", {}).get("schema")


def is_named_model(schema: dict | None) -> bool:
    """Un `$ref` a un componente (un modelo Pydantic con nombre) o una lista de ellos.

    Un handler sin `response_model` pero anotado con `-> dict[str, str]` también genera esquema, pero
    genérico y sin nombre (`{"type": "object", ...}`): eso es lo que esta guarda rechaza.
    """
    if not schema:
        return False
    if schema.get("type") == "array":
        return is_named_model(schema.get("items"))
    return "$ref" in schema


def field_names(schema: dict | None, components: dict, seen: set[str] | None = None) -> set[str]:
    """Todos los nombres de propiedad de un esquema, siguiendo `$ref`, listas, uniones y anidados."""
    if not schema:
        return set()
    seen = set() if seen is None else seen
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        if name in seen:
            return set()
        seen.add(name)
        return field_names(components[name], components, seen)
    names = set(schema.get("properties", {}))
    children = list(schema.get("properties", {}).values())
    children += [schema.get("items"), schema.get("additionalProperties")]
    children += schema.get("anyOf", []) + schema.get("allOf", []) + schema.get("oneOf", [])
    for child in children:
        if isinstance(child, dict):
            names |= field_names(child, components, seen)
    return names


def ref_name(schema: dict | None) -> str | None:
    return schema["$ref"].rsplit("/", 1)[-1] if schema and "$ref" in schema else None


def openapi_operations(api) -> tuple[list[tuple[str, str, dict]], dict]:
    spec = api.get("/openapi.json").json()
    operations = [
        (method.upper(), path, operation)
        for path, methods in spec["paths"].items()
        for method, operation in methods.items()
    ]
    return operations, spec["components"]["schemas"]


def test_the_app_still_has_the_audited_operations(api):
    # Si cambia, hay que auditar la ruta nueva y añadirla a docs/serialization-audit.md.
    # 35 de la auditoría + POST /telemetry/events, GET /telemetry/report, GET /api/v1/locations y las
    # tres de /reporting (sección 11 del documento).
    operations, _ = openapi_operations(api)
    assert len(operations) == 41


def test_every_json_response_is_a_named_model_except_the_named_exceptions(api):
    operations, _ = openapi_operations(api)
    without_model = {(method, path) for method, path, operation in operations if not is_named_model(success_schema(operation))}
    assert without_model == ROUTES_WITHOUT_RESPONSE_MODEL


def test_the_csv_exception_answers_a_file_not_json(api):
    operations, _ = openapi_operations(api)
    by_route = {(method, path): operation for method, path, operation in operations}
    for route in ROUTES_WITHOUT_RESPONSE_MODEL:
        assert list(success_response(by_route[route])["content"]) == ["text/csv"]


def test_no_response_exposes_passwords_hashes_or_reset_tokens(api):
    operations, components = openapi_operations(api)
    leaks = {
        (method, path): sorted(field_names(success_schema(operation), components) & SENSITIVE_FIELDS)
        for method, path, operation in operations
    }
    assert {route: fields for route, fields in leaks.items() if fields} == {}


def test_auth_flows_do_not_echo_the_email_but_me_does(api):
    operations, components = openapi_operations(api)
    fields = {(method, path): field_names(success_schema(operation), components) for method, path, operation in operations}

    assert {route for route in AUTH_ROUTES_WITHOUT_EMAIL if "email" in fields[route]} == set()
    assert "email" in fields[("GET", "/api/v1/auth/me")]


def test_writes_do_not_reuse_the_response_schema_as_input(api):
    operations, _ = openapi_operations(api)
    shared = set()
    for method, path, operation in operations:
        if method.lower() not in WRITE_METHODS or "requestBody" not in operation:
            continue
        content = operation["requestBody"]["content"]
        request = ref_name(content.get("application/json", {}).get("schema"))
        response = ref_name(success_schema(operation))
        if request and request == response:
            shared.add((method, path, request))
    assert shared == set()
