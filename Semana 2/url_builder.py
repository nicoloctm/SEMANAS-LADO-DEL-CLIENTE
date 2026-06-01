import urllib.parse
import re

class URLBuilder:
    def __init__(self, base_url: str):
        self.base_url = base_url
        if not self.base_url.endswith('/'):
            self.base_url += '/'

    def build_url(self, endpoint_template: str, path_params: dict = None, query_params: dict = None) -> str:
        """
        Construye una URL de forma segura.
        
        Args:
            endpoint_template: Cadena con marcadores como 'productos/{id}'
            path_params: Diccionario con los valores para los marcadores
            query_params: Diccionario con parámetros de consulta (?llave=valor)
            
        Returns:
            URL completa y sanitizada.
        """
        path_params = path_params or {}
        query_params = query_params or {}
        
        # Separar segmentos de la plantilla
        segments = endpoint_template.split('/')
        processed_segments = []
        
        for segment in segments:
            if segment.startswith('{') and segment.endswith('}'):
                param_name = segment[1:-1]
                if param_name not in path_params:
                    raise ValueError(f"Falta el parámetro de ruta requerido: '{param_name}'")
                
                val = path_params[param_name]
                
                # Validación de seguridad del tipo de dato
                if isinstance(val, bool):
                    raise ValueError(f"El parámetro '{param_name}' no puede ser un booleano.")
                
                if isinstance(val, (int, float)):
                    # Los números son inherentemente seguros en URL
                    escaped_val = str(val)
                elif isinstance(val, str):
                    # Proteger contra inyecciones y path traversal
                    # Si el valor contiene caracteres como '../' o '/' y no se escapan, se rompería la estructura
                    # urllib.parse.quote con safe="" reemplaza TODOS los caracteres especiales (incluidos '/' y '.')
                    escaped_val = urllib.parse.quote(val, safe="")
                else:
                    raise ValueError(f"Tipo de parámetro '{param_name}' no válido: {type(val).__name__}")
                
                processed_segments.append(escaped_val)
            else:
                # Segmento estático (ej. 'productos')
                processed_segments.append(segment)
                
        resolved_path = "/".join(processed_segments)
        
        # Combinar base_url con la ruta resuelta usando urljoin
        full_url = urllib.parse.urljoin(self.base_url, resolved_path)
        
        # Limpiar y codificar query params
        if query_params:
            clean_query = {}
            for k, v in query_params.items():
                if v is not None:
                    # Guardar llave y valor (urlencode se encargará de escapar caracteres especiales en ambos)
                    clean_query[k] = str(v)
            
            if clean_query:
                query_string = urllib.parse.urlencode(clean_query)
                full_url = f"{full_url}?{query_string}"
                
        return full_url

# Pruebas sencillas en el mismo archivo para demostrar seguridad
if __name__ == "__main__":
    builder = URLBuilder("http://localhost:3000/api/")
    
    print("=== PRUEBAS DE SEGURIDAD URLBUILDER ===")
    
    # Caso 1: Caso de uso normal
    url_normal = builder.build_url("productos/{id}", {"id": 42}, {"categoria": "miel"})
    print(f"Normal:   {url_normal}")
    
    # Caso 2: Intento de Path Traversal (../../etc/passwd)
    # Sin URLBuilder: f"http://localhost:3000/api/productos/{id}"
    # Si id = "../../etc/passwd" -> http://localhost:3000/api/productos/../../etc/passwd que equivale a http://localhost:3000/api/etc/passwd (Acceso no autorizado)
    id_malicioso = "../../etc/passwd"
    url_traversal = builder.build_url("productos/{id}", {"id": id_malicioso})
    print(f"Mitigado Traversal: {url_traversal}")
    
    # Caso 3: Inyección de Query Params
    # Si id = "42?admin=true"
    # Sin URLBuilder: f"http://localhost:3000/api/productos/{id}" -> http://localhost:3000/api/productos/42?admin=true
    id_inyeccion = "42?admin=true"
    url_inyeccion = builder.build_url("productos/{id}", {"id": id_inyeccion})
    print(f"Mitigado Inyección: {url_inyeccion}")
    
    # Caso 4: Caracteres Unicode extraños
    nombre_unicode = "miel orgánica 🐝"
    url_unicode = builder.build_url("productos", query_params={"nombre": nombre_unicode})
    print(f"Mitigado Unicode:   {url_unicode}")
