import unittest
from validadores import validar_producto, validar_lista_productos, ValidationError

class TestValidadores(unittest.TestCase):

    def setUp(self):
        # Un producto válido de base para modificarlo en las pruebas de error
        self.producto_valido = {
            "id": 42,
            "nombre": "Miel orgánica",
            "precio": 150.00,
            "categoria": "miel",
            "disponible": True,
            "descripcion": "Miel natural pura de abeja.",
            "productor": {
                "id": 7,
                "nombre": "Apiarios del Valle"
            },
            "creado_en": "2024-01-15T10:30:00Z"
        }

    def test_happy_path(self):
        # Probar que el producto válido pasa sin problemas
        resultado = validar_producto(self.producto_valido)
        self.assertEqual(resultado["id"], 42)
        self.assertEqual(resultado["nombre"], "Miel orgánica")

    # --- 5 CASOS DE FALLO RECHAZADOS POR LA FUNCIÓN ---

    def test_fallo_1_falta_campo_obligatorio(self):
        # Caso 1: Falta el campo obligatorio "nombre"
        prod_invalido = self.producto_valido.copy()
        del prod_invalido["nombre"]
        
        with self.assertRaises(ValidationError) as ctx:
            validar_producto(prod_invalido)
        self.assertIn("Falta el campo obligatorio: 'nombre'", str(ctx.exception))

    def test_fallo_2_precio_tipo_incorrecto(self):
        # Caso 2: El precio es un texto en lugar de número
        prod_invalido = self.producto_valido.copy()
        prod_invalido["precio"] = "ciento cincuenta"
        
        with self.assertRaises(ValidationError) as ctx:
            validar_producto(prod_invalido)
        self.assertIn("El campo 'precio' debe ser un número", str(ctx.exception))

    def test_fallo_3_precio_negativo(self):
        # Caso 3: El precio es menor o igual a cero
        prod_invalido = self.producto_valido.copy()
        prod_invalido["precio"] = -10.50
        
        with self.assertRaises(ValidationError) as ctx:
            validar_producto(prod_invalido)
        self.assertIn("El precio debe ser un número positivo mayor a 0", str(ctx.exception))

    def test_fallo_4_categoria_invalida(self):
        # Caso 4: La categoría no está en la lista permitida
        prod_invalido = self.producto_valido.copy()
        prod_invalido["categoria"] = "refrescos"
        
        with self.assertRaises(ValidationError) as ctx:
            validar_producto(prod_invalido)
        self.assertIn("Categoría no válida: 'refrescos'", str(ctx.exception))

    def test_fallo_5_fecha_formato_incorrecto(self):
        # Caso 5: La fecha de creación no cumple con ISO 8601
        prod_invalido = self.producto_valido.copy()
        prod_invalido["creado_en"] = "2024/01/15 10:30:00"
        
        with self.assertRaises(ValidationError) as ctx:
            validar_producto(prod_invalido)
        self.assertIn("no tiene un formato de fecha ISO 8601 válido", str(ctx.exception))

    # --- 1 CASO DE FALLO PROPIO (ADICIONAL) ---

    def test_fallo_6_productor_id_tipo_incorrecto(self):
        # Caso 6 (Propio): El productor tiene un ID que es texto ("siete") en lugar de entero
        prod_invalido = self.producto_valido.copy()
        prod_invalido["productor"] = {
            "id": "siete",
            "nombre": "Apiarios del Valle"
        }
        
        with self.assertRaises(ValidationError) as ctx:
            validar_producto(prod_invalido)
        self.assertIn("El 'id' del productor debe ser un número entero", str(ctx.exception))

    def test_fallo_7_id_es_booleano(self):
        # Caso adicional propio: El id del producto es un booleano (True).
        # En Python, isinstance(True, int) es True, por lo que una validación ingenua lo aceptaría.
        prod_invalido = self.producto_valido.copy()
        prod_invalido["id"] = True
        
        with self.assertRaises(ValidationError) as ctx:
            validar_producto(prod_invalido)
        self.assertIn("El campo 'id' debe ser un número entero", str(ctx.exception))

    def test_validar_lista_vacia(self):
        # Probar que validar_lista_productos maneja listas vacías
        self.assertEqual(validar_lista_productos([]), [])

    def test_validar_lista_con_error(self):
        # Probar que validar_lista_productos reporta el índice exacto que falló
        prod_invalido = self.producto_valido.copy()
        prod_invalido["precio"] = 0
        lista = [self.producto_valido, prod_invalido]
        
        with self.assertRaises(ValidationError) as ctx:
            validar_lista_productos(lista)
        self.assertIn("Error en el producto del índice 1", str(ctx.exception))

if __name__ == "__main__":
    unittest.main()
