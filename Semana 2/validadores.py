import re
from datetime import datetime

class ValidationError(Exception):
    """Excepción que se lanza cuando los datos del servidor no son válidos."""
    pass

def validar_producto(data: dict) -> dict:
    """
    Valida que un diccionario de producto cumpla con el esquema requerido.
    Lanza ValidationError si encuentra algún error.
    """
    if not isinstance(data, dict):
        raise ValidationError("El producto debe ser un diccionario.")

    # 1. Campos obligatorios
    campos_obligatorios = ["id", "nombre", "precio", "categoria"]
    for campo in campos_obligatorios:
        if campo not in data:
            raise ValidationError(f"Falta el campo obligatorio: '{campo}'")

    # 2. Validación de tipos
    # ID
    if not isinstance(data["id"], int) or isinstance(data["id"], bool): # En python bool es subclase de int, hay que cuidar eso
        raise ValidationError(f"El campo 'id' debe ser un número entero, recibido: {type(data['id']).__name__}")
    
    # Nombre
    if not isinstance(data["nombre"], str):
        raise ValidationError(f"El campo 'nombre' debe ser texto (str), recibido: {type(data['nombre']).__name__}")
    if len(data["nombre"].strip()) < 3:
        raise ValidationError("El nombre del producto debe tener al menos 3 caracteres.")
    if len(data["nombre"]) > 50:
        raise ValidationError("El nombre del producto no debe exceder los 50 caracteres.")

    # Precio
    # Aceptamos int o float (luego lo tratamos como float)
    if not isinstance(data["precio"], (int, float)) or isinstance(data["precio"], bool):
        raise ValidationError(f"El campo 'precio' debe ser un número, recibido: {type(data['precio']).__name__}")
    
    # Validar valor del precio
    try:
        precio_val = float(data["precio"])
    except (ValueError, TypeError):
        raise ValidationError("El precio no se puede convertir a número decimal.")

    if precio_val <= 0:
        raise ValidationError(f"El precio debe ser un número positivo mayor a 0, recibido: {data['precio']}")

    # Categoría
    categorias_validas = ['frutas', 'verduras', 'lacteos', 'miel', 'conservas']
    if not isinstance(data["categoria"], str):
        raise ValidationError(f"El campo 'categoria' debe ser texto (str), recibido: {type(data['categoria']).__name__}")
    if data["categoria"] not in categorias_validas:
        raise ValidationError(f"Categoría no válida: '{data['categoria']}'. Debe ser una de: {categorias_validas}")

    # Disponible (es opcional según openapi o obligatorio en algunas partes, pero la guía dice que es requerido para el tipo)
    if "disponible" in data:
        if not isinstance(data["disponible"], bool):
            raise ValidationError(f"El campo 'disponible' debe ser un boleano (True/False), recibido: {type(data['disponible']).__name__}")

    # 3. Campos opcionales
    # Descripción
    if "descripcion" in data and data["descripcion"] is not None:
        if not isinstance(data["descripcion"], str):
            raise ValidationError(f"El campo 'descripcion' debe ser texto (str), recibido: {type(data['descripcion']).__name__}")
        if len(data["descripcion"]) > 500:
            raise ValidationError("La descripción no debe exceder los 500 caracteres.")

    # Productor
    if "productor" in data and data["productor"] is not None:
        productor = data["productor"]
        if not isinstance(productor, dict):
            raise ValidationError(f"El campo 'productor' debe ser un objeto/diccionario, recibido: {type(productor).__name__}")
        
        # Campos obligatorios del productor si existe
        if "id" not in productor:
            raise ValidationError("Al objeto 'productor' le falta el campo obligatorio: 'id'")
        if "nombre" not in productor:
            raise ValidationError("Al objeto 'productor' le falta el campo obligatorio: 'nombre'")
        
        if not isinstance(productor["id"], int) or isinstance(productor["id"], bool):
            raise ValidationError(f"El 'id' del productor debe ser un número entero, recibido: {type(productor['id']).__name__}")
        if not isinstance(productor["nombre"], str):
            raise ValidationError(f"El 'nombre' del productor debe ser texto (str), recibido: {type(productor['nombre']).__name__}")

    # Creado en (Fecha ISO 8601)
    if "creado_en" in data and data["creado_en"] is not None:
        fecha_str = data["creado_en"]
        if not isinstance(fecha_str, str):
            raise ValidationError(f"El campo 'creado_en' debe ser texto (str), recibido: {type(fecha_str).__name__}")
        
        # Validar formato ISO 8601
        try:
            # Reemplazar Z por +00:00 para soportar formatos de zona horaria en python
            clean_fecha = fecha_str.replace('Z', '+00:00')
            datetime.fromisoformat(clean_fecha)
        except ValueError:
            raise ValidationError(f"El campo 'creado_en' no tiene un formato de fecha ISO 8601 válido: '{fecha_str}'")

    return data

def validar_lista_productos(data: list) -> list:
    """
    Valida una lista de productos.
    Lanza ValidationError si no es lista o si algún producto falla la validación.
    """
    if not isinstance(data, list):
        raise ValidationError(f"Se esperaba una lista de productos, recibido: {type(data).__name__}")
    
    productos_validados = []
    for idx, item in enumerate(data):
        try:
            validado = validar_producto(item)
            productos_validados.append(validado)
        except ValidationError as e:
            raise ValidationError(f"Error en el producto del índice {idx}: {str(e)}")
            
    return productos_validados
