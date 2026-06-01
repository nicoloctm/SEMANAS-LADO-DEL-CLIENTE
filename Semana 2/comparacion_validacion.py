import time
import json
from datetime import datetime

# --- 1. ESTRATEGIA 1: VALIDACIÓN MANUAL ---
from validadores import validar_producto as validar_manual

# --- 2. ESTRATEGIA 2: PYDANTIC (Se importa condicionalmente si está instalado) ---
PYDANTIC_DISPONIBLE = False
try:
    from pydantic import BaseModel, Field, field_validator, ValidationError as PydanticValidationError
    from typing import Optional

    class ProductorModel(BaseModel):
        id: int
        nombre: str

    class ProductoModel(BaseModel):
        id: int
        nombre: str = Field(min_length=3, max_length=50)
        precio: float = Field(gt=0)
        categoria: str
        disponible: bool = True
        descripcion: Optional[str] = Field(None, max_length=500)
        productor: Optional[ProductorModel] = None
        creado_en: Optional[datetime] = None

        @field_validator('categoria')
        @classmethod
        def validar_categoria(cls, v: str) -> str:
            categorias_validas = ['frutas', 'verduras', 'lacteos', 'miel', 'conservas']
            if v not in categorias_validas:
                raise ValueError(f"Debe ser una de: {categorias_validas}")
            return v
            
    def validar_con_pydantic(data: dict):
        # Pydantic automáticamente parsea la fecha si es formato ISO
        model = ProductoModel(**data)
        return model.model_dump()
        
    PYDANTIC_DISPONIBLE = True
except ImportError:
    def validar_con_pydantic(data: dict):
        raise NotImplementedError("Pydantic no está instalado.")

# --- 3. ESTRATEGIA 3: JSON SCHEMA (Se importa condicionalmente) ---
JSONSCHEMA_DISPONIBLE = False
try:
    import jsonschema
    from jsonschema import validate
    
    SCHEMA = {
        "type": "object",
        "required": ["id", "nombre", "precio", "categoria"],
        "properties": {
            "id": {"type": "integer"},
            "nombre": {"type": "string", "minLength": 3, "maxLength": 50},
            "precio": {"type": "number", "exclusiveMinimum": 0},
            "categoria": {"type": "string", "enum": ["frutas", "verduras", "lacteos", "miel", "conservas"]},
            "disponible": {"type": "boolean"},
            "descripcion": {"type": "string", "maxLength": 500},
            "productor": {
                "type": "object",
                "required": ["id", "nombre"],
                "properties": {
                    "id": {"type": "integer"},
                    "nombre": {"type": "string"}
                }
            },
            "creado_en": {
                "type": "string", 
                "pattern": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$"
            }
        }
    }
    
    def validar_con_jsonschema(data: dict):
        validate(instance=data, schema=SCHEMA)
        return data
        
    JSONSCHEMA_DISPONIBLE = True
except ImportError:
    def validar_con_jsonschema(data: dict):
        raise NotImplementedError("jsonschema no está instalado.")


# --- BENCHMARK ---
if __name__ == "__main__":
    producto_prueba = {
        "id": 42,
        "nombre": "Miel orgánica",
        "precio": 150.00,
        "categoria": "miel",
        "disponible": True,
        "descripcion": "Miel natural de flores silvestres.",
        "productor": {
            "id": 7,
            "nombre": "Apiarios del Valle"
        },
        "creado_en": "2024-01-15T10:30:00Z"
    }

    print("=== COMPARATIVA DE ESTRATEGIAS DE VALIDACIÓN ===")
    print(f"Pydantic instalado: {PYDANTIC_DISPONIBLE}")
    print(f"jsonschema instalado: {JSONSCHEMA_DISPONIBLE}\n")

    iteraciones = 1000
    print(f"Corriendo validación de {iteraciones} productos para cada estrategia...\n")

    # 1. Benchmark Manual
    t_start = time.perf_counter()
    for _ in range(iteraciones):
        validar_manual(producto_prueba)
    t_manual = time.perf_counter() - t_start
    print(f"1. Validación Manual: {t_manual:.6f} segundos ({t_manual/iteraciones*1000000:.2f} µs por producto)")

    # 2. Benchmark Pydantic
    if PYDANTIC_DISPONIBLE:
        t_start = time.perf_counter()
        for _ in range(iteraciones):
            validar_con_pydantic(producto_prueba)
        t_pydantic = time.perf_counter() - t_start
        print(f"2. Pydantic v2:        {t_pydantic:.6f} segundos ({t_pydantic/iteraciones*1000000:.2f} µs por producto)")
    else:
        print("2. Pydantic v2:        No disponible (no instalado)")

    # 3. Benchmark JSON Schema
    if JSONSCHEMA_DISPONIBLE:
        t_start = time.perf_counter()
        for _ in range(iteraciones):
            validar_con_jsonschema(producto_prueba)
        t_jsonschema = time.perf_counter() - t_start
        print(f"3. JSON Schema:       {t_jsonschema:.6f} segundos ({t_jsonschema/iteraciones*1000000:.2f} µs por producto)")
    else:
        print("3. JSON Schema:       No disponible (no instalado)")
