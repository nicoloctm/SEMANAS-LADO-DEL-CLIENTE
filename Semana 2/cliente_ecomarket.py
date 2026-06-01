import requests
from url_builder import URLBuilder
from validadores import validar_producto, validar_lista_productos, ValidationError as SchemaValidationError

# Configuración centralizada
BASE_URL = "http://localhost:3000/api/"
TIMEOUT = 10  # segundos

# --- EXCEPCIONES PERSONALIZADAS ---
class EcoMarketError(Exception):
    """Error base para el cliente de EcoMarket."""
    pass

class ValidationError(EcoMarketError):
    """Errores de validación del cliente o 400 Bad Request del servidor."""
    pass

class AuthenticationError(EcoMarketError):
    """Error de autenticación o sesión expirada (401 Unauthorized)."""
    pass

class NotFoundError(EcoMarketError):
    """Recurso no encontrado en el servidor (404 Not Found)."""
    pass

class ConflictError(EcoMarketError):
    """Conflicto en el servidor, como producto duplicado (409 Conflict)."""
    pass

class ServerError(EcoMarketError):
    """Error interno del servidor (5xx) - potencialmente reintentable."""
    pass


# Inicializar el constructor de URLs
url_builder = URLBuilder(BASE_URL)

def _verificar_respuesta(response):
    """
    Verifica el código de estado HTTP y el Content-Type.
    Lanza la excepción personalizada correspondiente si hay fallos.
    """
    status = response.status_code

    # Capa 1: Verificar códigos de error HTTP
    if status == 400:
        try:
            body = response.json()
            msg = body.get("mensaje", "Datos de petición incorrectos.")
        except Exception:
            msg = f"Error 400 Bad Request: {response.text}"
        raise ValidationError(msg)

    elif status == 401:
        try:
            body = response.json()
            msg = body.get("mensaje", "No autorizado. Revisa tus credenciales.")
        except Exception:
            msg = "No autorizado. Su sesión ha expirado."
        raise AuthenticationError(msg)

    elif status == 404:
        try:
            body = response.json()
            msg = body.get("mensaje", "El recurso solicitado no existe.")
        except Exception:
            msg = "Recurso no encontrado (404)."
        raise NotFoundError(msg)

    elif status == 409:
        try:
            body = response.json()
            msg = body.get("mensaje", "Existe un conflicto con este recurso.")
        except Exception:
            msg = "Conflicto con el recurso (409)."
        raise ConflictError(msg)

    elif status >= 500:
        raise ServerError(f"Error interno del servidor ({status}): {response.text}")

    elif status >= 300:
        raise EcoMarketError(f"Redirección o estado no manejado ({status}): {response.text}")

    # Capa 2: Content-Type (si la respuesta tiene cuerpo y no es un 204 No Content)
    if status != 204:
        content_type = response.headers.get('Content-Type', '')
        if 'application/json' not in content_type:
            raise ValidationError(f"El servidor no respondió con JSON válido. Recibido: {content_type}")

    return response


def listar_productos(categoria=None, orden=None, nombre=None):
    """
    GET /productos con filtros opcionales.
    
    Ejemplo de uso:
        productos = listar_productos(categoria="miel", nombre="orgánica")
    """
    # Construir URL de forma segura
    query_params = {}
    if categoria:
        query_params['categoria'] = categoria
    if orden:
        query_params['orden'] = orden
    if nombre:
        query_params['nombre'] = nombre
        
    url = url_builder.build_url("productos", query_params=query_params)
    
    response = requests.get(url, timeout=TIMEOUT)
    _verificar_respuesta(response)
    
    datos = response.json()
    
    # El API puede retornar un diccionario paginado: {"total": 1, "page": 1, "limit": 10, "data": [...]}
    # o una lista directa. Soportamos ambos casos.
    if isinstance(datos, dict) and "data" in datos:
        lista_cruda = datos["data"]
        # Validar la lista de productos antes de usarla
        try:
            validar_lista_productos(lista_cruda)
        except SchemaValidationError as e:
            raise ValidationError(f"Los datos de productos paginados del servidor son inválidos: {str(e)}")
        return datos
    else:
        # Es una lista directa
        try:
            return validar_lista_productos(datos)
        except SchemaValidationError as e:
            raise ValidationError(f"Los datos de la lista de productos del servidor son inválidos: {str(e)}")


def obtener_producto(producto_id):
    """
    GET /productos/{id}
    
    Ejemplo de uso:
        producto = obtener_producto(42)
    """
    url = url_builder.build_url("productos/{id}", path_params={"id": producto_id})
    
    response = requests.get(url, timeout=TIMEOUT)
    _verificar_respuesta(response)
    
    producto_datos = response.json()
    
    # Validar el esquema del producto
    try:
        return validar_producto(producto_datos)
    except SchemaValidationError as e:
        raise ValidationError(f"El producto retornado del servidor no cumple con el esquema: {str(e)}")


def crear_producto(datos: dict, token: str = None) -> dict:
    """
    POST /productos
    Crea un nuevo producto en el catálogo. Requiere token de autenticación.
    
    Ejemplo de uso:
        nuevo = crear_producto({"nombre": "Jugo de naranja", "precio": 35.0, ...}, token="jwt-token")
    """
    url = url_builder.build_url("productos")
    
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    response = requests.post(url, json=datos, headers=headers, timeout=TIMEOUT)
    _verificar_respuesta(response)
    
    producto_creado = response.json()
    
    # Validar que el producto recién creado por el servidor sea válido
    try:
        return validar_producto(producto_creado)
    except SchemaValidationError as e:
        raise ValidationError(f"El servidor guardó el producto pero devolvió datos inválidos: {str(e)}")


def actualizar_producto_total(producto_id: int, datos: dict, token: str = None) -> dict:
    """
    PUT /productos/{id}
    Reemplaza COMPLETAMENTE un producto. Se deben enviar todos los campos obligatorios.
    
    Ejemplo de uso:
        actualizado = actualizar_producto_total(42, {"nombre": "Miel pura", "precio": 160.0, ...}, token="jwt-token")
    """
    url = url_builder.build_url("productos/{id}", path_params={"id": producto_id})
    
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    response = requests.put(url, json=datos, headers=headers, timeout=TIMEOUT)
    _verificar_respuesta(response)
    
    producto_actualizado = response.json()
    
    # Validar la respuesta
    try:
        return validar_producto(producto_actualizado)
    except SchemaValidationError as e:
        raise ValidationError(f"El servidor actualizó (PUT) el producto pero devolvió datos inválidos: {str(e)}")


def actualizar_producto_parcial(producto_id: int, campos: dict, token: str = None) -> dict:
    """
    PATCH /productos/{id}
    Modifica PARCIALMENTE un producto. Solo se envían los campos a cambiar.
    
    Ejemplo de uso:
        actualizado = actualizar_producto_parcial(42, {"precio": 170.00}, token="jwt-token")
    """
    url = url_builder.build_url("productos/{id}", path_params={"id": producto_id})
    
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    response = requests.patch(url, json=campos, headers=headers, timeout=TIMEOUT)
    _verificar_respuesta(response)
    
    producto_actualizado = response.json()
    
    # Validar la respuesta
    try:
        return validar_producto(producto_actualizado)
    except SchemaValidationError as e:
        raise ValidationError(f"El servidor actualizó (PATCH) el producto pero devolvió datos inválidos: {str(e)}")


def eliminar_producto(producto_id: int, token: str = None) -> bool:
    """
    DELETE /productos/{id}
    Elimina un producto del catálogo.
    
    Ejemplo de uso:
        exito = eliminar_producto(42, token="jwt-token")
    """
    url = url_builder.build_url("productos/{id}", path_params={"id": producto_id})
    
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    response = requests.delete(url, headers=headers, timeout=TIMEOUT)
    _verificar_respuesta(response)
    
    # Si devuelve 204 No Content, fue exitoso
    if response.status_code == 204:
        return True
        
    return False
