import time
from enum import Enum

class EstadoCircuito(Enum):
    CERRADO = "CERRADO"
    ABIERTO = "ABIERTO"
    SEMIABIERTO = "SEMIABIERTO"

class CircuitOpenError(Exception):
    """Excepción que se lanza cuando el circuito está abierto y rechaza peticiones."""
    pass

class CircuitBreaker:
    def __init__(self, umbral=5, timeout=10):
        self.estado = EstadoCircuito.CERRADO
        self._umbral = umbral
        self._timeout = timeout
        self._fallos = 0
        self._tiempo_apertura = None
        self._peticion_de_prueba_en_curso = False # Para coordinar SEMIABIERTO (INV-A2)
        self.on_state_change = None # Callback observable (onCircuitOpen, onCircuitClosed, etc.)

    def _cambiar_estado(self, nuevo_estado):
        if self.estado != nuevo_estado:
            viejo_estado = self.estado
            self.estado = nuevo_estado
            if self.on_state_change:
                self.on_state_change(viejo_estado, nuevo_estado)

    def _segundos_restantes(self):
        if not self._tiempo_apertura:
            return 0
        transcurrido = time.time() - self._tiempo_apertura
        restante = self._timeout - transcurrido
        return max(0.0, restante)

    async def ejecutar(self, fn):
        """
        Ejecuta la función asíncrona envuelta en la lógica del Circuit Breaker.
        Cumple estrictamente con INV-A1 (no toca JWT) e INV-A2 (solo pasa 1 en SEMIABIERTO).
        """
        # 1. Verificar si el circuito está abierto y el timeout ya expiró
        if self.estado == EstadoCircuito.ABIERTO:
            if time.time() - self._tiempo_apertura >= self._timeout:
                self.estado = EstadoCircuito.SEMIABIERTO
                self._peticion_de_prueba_en_curso = False
            else:
                # Fail-fast inmediato
                restante = self._segundos_restantes()
                raise CircuitOpenError(f"Circuito abierto. Reintente en {restante:.0f}s")

        # 2. Si está en SEMIABIERTO, coordinar para que pase exactamente una petición
        if self.estado == EstadoCircuito.SEMIABIERTO:
            if self._peticion_de_prueba_en_curso:
                # Las peticiones concurrentes adicionales en SEMIABIERTO fallan de inmediato
                raise CircuitOpenError("Circuito en estado SEMIABIERTO. Ya hay una petición de prueba en curso.")
            self._peticion_de_prueba_en_curso = True

        # 3. Intentar ejecutar la petición
        try:
            # Soportar funciones asíncronas
            resultado = await fn()
            self._on_exito()
            return resultado
        except Exception as e:
            self._on_fallo(e)
            raise

    def _on_exito(self):
        """Maneja el éxito de una petición (transiciona a CERRADO y limpia contadores)."""
        self._cambiar_estado(EstadoCircuito.CERRADO)  # dispara callback
        self._fallos = 0  # INV-A3: Limpiar fallos al cerrar
        self._peticion_de_prueba_en_curso = False
        self._tiempo_apertura = None

    def _on_fallo(self, error):
        """Maneja el fallo de una petición."""
        # Liberar la bandera de prueba en caso de fallo en SEMIABIERTO
        self._peticion_de_prueba_en_curso = False

        if not self._es_fallo_servidor(error):
            # INV-A4: Errores 401/403 (de cliente) no incrementan fallos
            return

        self._fallos += 1
        
        # Si el circuito estaba en SEMIABIERTO y falló la prueba, vuelve a ABIERTO reiniciando el timeout
        if self.estado == EstadoCircuito.SEMIABIERTO or self._fallos >= self._umbral:
            self._cambiar_estado(EstadoCircuito.ABIERTO)  # dispara callback
            self._tiempo_apertura = time.time()

    def _es_fallo_servidor(self, error):
        """
        Determina si un error es del servidor (5xx, timeouts o problemas de red)
        y no del cliente (como 401, 403, 404).
        """
        # Analizar el mensaje del error
        msg = str(error).lower()
        
        # Si el mensaje indica explícitamente 401, 403 o Unauthorized/Forbidden, no es fallo del servidor
        if '401' in msg or '403' in msg or 'unauthorized' in msg or 'forbidden' in msg or 'permission' in msg:
            return False
            
        # Si es un fallo 5xx, timeout o error de conexión, es fallo del servidor
        return '5' in msg or 'timeout' in msg or 'connection' in msg or '503' in msg or '500' in msg
