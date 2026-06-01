import pytest
import responses
import requests
from cliente_ecomarket import (
    listar_productos,
    obtener_producto,
    crear_producto,
    actualizar_producto_total,
    actualizar_producto_parcial,
    eliminar_producto,
    ValidationError,
    AuthenticationError,
    NotFoundError,
    ConflictError,
    ServerError,
    EcoMarketError
)
from retry import with_retry

# URL base mockeada
BASE_URL = "http://localhost:3000/api/"

# Datos de prueba correctos
PRODUCTO_VALIDO = {
    "id": 42,
    "nombre": "Miel orgánica",
    "precio": 150.00,
    "categoria": "miel",
    "disponible": True,
    "descripcion": "Miel de flores.",
    "productor": {
        "id": 7,
        "nombre": "Apiarios del Valle"
    },
    "creado_en": "2024-01-15T10:30:00Z"
}

# --- 1. HAPPY PATH TESTS (6 TESTS) ---

@responses.activate
def test_listar_productos_happy_path():
    responses.add(
        responses.GET,
        f"{BASE_URL}productos",
        json=[PRODUCTO_VALIDO],
        status=200,
        content_type="application/json"
    )
    resultado = listar_productos()
    assert len(resultado) == 1
    assert resultado[0]["nombre"] == "Miel orgánica"

@responses.activate
def test_obtener_producto_happy_path():
    responses.add(
        responses.GET,
        f"{BASE_URL}productos/42",
        json=PRODUCTO_VALIDO,
        status=200,
        content_type="application/json"
    )
    resultado = obtener_producto(42)
    assert resultado["id"] == 42
    assert resultado["nombre"] == "Miel orgánica"

@responses.activate
def test_crear_producto_happy_path():
    responses.add(
        responses.POST,
        f"{BASE_URL}productos",
        json=PRODUCTO_VALIDO,
        status=201,
        content_type="application/json"
    )
    # Enviamos los datos para crear
    datos_creacion = {
        "nombre": "Miel orgánica",
        "precio": 150.00,
        "categoria": "miel",
        "disponible": True
    }
    resultado = crear_producto(datos_creacion, token="valido")
    assert resultado["id"] == 42
    assert resultado["nombre"] == "Miel orgánica"

@responses.activate
def test_actualizar_producto_total_happy_path():
    responses.add(
        responses.PUT,
        f"{BASE_URL}productos/42",
        json=PRODUCTO_VALIDO,
        status=200,
        content_type="application/json"
    )
    resultado = actualizar_producto_total(42, PRODUCTO_VALIDO, token="valido")
    assert resultado["precio"] == 150.00

@responses.activate
def test_actualizar_producto_parcial_happy_path():
    responses.add(
        responses.PATCH,
        f"{BASE_URL}productos/42",
        json=PRODUCTO_VALIDO,
        status=200,
        content_type="application/json"
    )
    resultado = actualizar_producto_parcial(42, {"precio": 150.00}, token="valido")
    assert resultado["precio"] == 150.00

@responses.activate
def test_eliminar_producto_happy_path():
    responses.add(
        responses.DELETE,
        f"{BASE_URL}productos/42",
        status=204
    )
    resultado = eliminar_producto(42, token="valido")
    assert resultado is True


# --- 2. HTTP ERROR TESTS (8 TESTS) ---

@responses.activate
def test_crear_producto_400_bad_request():
    responses.add(
        responses.POST,
        f"{BASE_URL}productos",
        json={"mensaje": "El nombre es obligatorio"},
        status=400,
        content_type="application/json"
    )
    with pytest.raises(ValidationError) as exc_info:
        crear_producto({"precio": 10.0}, token="valido")
    assert "El nombre es obligatorio" in str(exc_info.value)

@responses.activate
def test_cliente_401_unauthorized():
    responses.add(
        responses.POST,
        f"{BASE_URL}productos",
        json={"mensaje": "Token inválido"},
        status=401,
        content_type="application/json"
    )
    with pytest.raises(AuthenticationError) as exc_info:
        crear_producto(PRODUCTO_VALIDO, token="invalido")
    assert "Token inválido" in str(exc_info.value)

@responses.activate
def test_obtener_producto_404_not_found():
    responses.add(
        responses.GET,
        f"{BASE_URL}productos/999",
        json={"mensaje": "Producto no existe"},
        status=404,
        content_type="application/json"
    )
    with pytest.raises(NotFoundError) as exc_info:
        obtener_producto(999)
    assert "Producto no existe" in str(exc_info.value)

@responses.activate
def test_actualizar_producto_total_404_not_found():
    responses.add(
        responses.PUT,
        f"{BASE_URL}productos/999",
        json={"mensaje": "No se puede actualizar"},
        status=404,
        content_type="application/json"
    )
    with pytest.raises(NotFoundError):
        actualizar_producto_total(999, PRODUCTO_VALIDO, token="valido")

@responses.activate
def test_eliminar_producto_404_not_found():
    responses.add(
        responses.DELETE,
        f"{BASE_URL}productos/999",
        json={"mensaje": "No existe"},
        status=404,
        content_type="application/json"
    )
    with pytest.raises(NotFoundError):
        eliminar_producto(999, token="valido")

@responses.activate
def test_crear_producto_409_conflict():
    responses.add(
        responses.POST,
        f"{BASE_URL}productos",
        json={"mensaje": "Producto con este SKU ya existe"},
        status=409,
        content_type="application/json"
    )
    with pytest.raises(ConflictError) as exc_info:
        crear_producto(PRODUCTO_VALIDO, token="valido")
    assert "Producto con este SKU ya existe" in str(exc_info.value)

@responses.activate
def test_cliente_500_internal_server_error():
    responses.add(
        responses.GET,
        f"{BASE_URL}productos/42",
        body="Error grave interno",
        status=500
    )
    with pytest.raises(ServerError) as exc_info:
        obtener_producto(42)
    assert "Error interno del servidor (500)" in str(exc_info.value)

@responses.activate
def test_cliente_503_service_unavailable():
    responses.add(
        responses.GET,
        f"{BASE_URL}productos/42",
        body="Servicio temporalmente no disponible",
        status=503
    )
    with pytest.raises(ServerError) as exc_info:
        obtener_producto(42)
    assert "Error interno del servidor (503)" in str(exc_info.value)


# --- 3. EDGE CASES (6 TESTS) ---

@responses.activate
def test_edge_cuerpo_vacio_con_200():
    responses.add(
        responses.GET,
        f"{BASE_URL}productos/42",
        body="",
        status=200,
        content_type="application/json"
    )
    # Intentar parsear un cuerpo vacío como JSON fallará al intentar response.json()
    with pytest.raises(Exception):
        obtener_producto(42)

@responses.activate
def test_edge_content_type_incorrecto_text_html():
    responses.add(
        responses.GET,
        f"{BASE_URL}productos/42",
        body="<html>Error 502 Gateway</html>",
        status=200,
        content_type="text/html"
    )
    with pytest.raises(ValidationError) as exc_info:
        obtener_producto(42)
    assert "El servidor no respondió con JSON válido" in str(exc_info.value)

@responses.activate
def test_edge_json_valido_pero_estructura_incorrecta():
    # Falta el campo obligatorio "precio"
    producto_sin_precio = {
        "id": 42,
        "nombre": "Miel sin precio",
        "categoria": "miel"
    }
    responses.add(
        responses.GET,
        f"{BASE_URL}productos/42",
        json=producto_sin_precio,
        status=200,
        content_type="application/json"
    )
    with pytest.raises(ValidationError) as exc_info:
        obtener_producto(42)
    assert "Falta el campo obligatorio: 'precio'" in str(exc_info.value)

@responses.activate
def test_edge_timeout_servidor():
    responses.add(
        responses.GET,
        f"{BASE_URL}productos/42",
        body=requests.exceptions.Timeout("El servidor tardó demasiado")
    )
    with pytest.raises(requests.exceptions.Timeout):
        obtener_producto(42)

@responses.activate
def test_edge_precio_como_string():
    # El precio es "ciento cincuenta"
    producto_precio_str = PRODUCTO_VALIDO.copy()
    producto_precio_str["precio"] = "gratis"
    responses.add(
        responses.GET,
        f"{BASE_URL}productos/42",
        json=producto_precio_str,
        status=200,
        content_type="application/json"
    )
    with pytest.raises(ValidationError) as exc_info:
        obtener_producto(42)
    assert "El campo 'precio' debe ser un número" in str(exc_info.value)

@responses.activate
def test_edge_lista_productos_vacia():
    responses.add(
        responses.GET,
        f"{BASE_URL}productos",
        json=[],
        status=200,
        content_type="application/json"
    )
    resultado = listar_productos()
    assert resultado == []


# --- 4. TESTS PROPIOS ADICIONALES (2 TESTS) ---

@responses.activate
def test_propio_buscar_por_nombre_query_param():
    # Verificamos que se añadan los parámetros de consulta (?nombre=miel) y que devuelva la respuesta
    responses.add(
        responses.GET,
        f"{BASE_URL}productos?nombre=miel",
        json=[PRODUCTO_VALIDO],
        status=200,
        content_type="application/json"
    )
    resultado = listar_productos(nombre="miel")
    assert len(resultado) == 1
    assert resultado[0]["id"] == 42

# Para probar el decorador de reintentos, creamos una función decorada de prueba
@with_retry(max_retries=2, base_delay=0.1)
def funcion_de_prueba_con_retry():
    # Simula hacer un GET a productos/42
    return obtener_producto(42)

@responses.activate
def test_propio_decorador_retry_exito_tras_fallos():
    # Simulamos que falla las primeras 2 veces con 503 Service Unavailable
    # Y la tercera tiene éxito (intento 0: falla, intento 1: falla, intento 2: exito)
    responses.add(
        responses.GET,
        f"{BASE_URL}productos/42",
        body="Servicio caído",
        status=503
    )
    responses.add(
        responses.GET,
        f"{BASE_URL}productos/42",
        body="Servicio caído",
        status=503
    )
    responses.add(
        responses.GET,
        f"{BASE_URL}productos/42",
        json=PRODUCTO_VALIDO,
        status=200,
        content_type="application/json"
    )
    
    # Debe tener éxito después de reintentar
    resultado = funcion_de_prueba_con_retry()
    assert resultado["id"] == 42
    # Deben haberse registrado 3 peticiones en responses
    assert len(responses.calls) == 3
