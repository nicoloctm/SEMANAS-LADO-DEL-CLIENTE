"""
DECISIONES DE DISEÑO — Hito 1 (Monitor de Inventario y Pedidos)
=======================================================
1. TIMEOUT: 10s → Trade-off: Evita que el cliente se congele indefinidamente 
   esperando una respuesta. Se sacrifica paciencia ante redes muy lentas.
   Decisión: Adecuado para EcoMarket para no bloquear UI.
2. REINTENTOS 5xx: 3 reintentos → Trade-off: Permite superar caídas 
   temporales del servidor, pero alarga el tiempo de fallo definitivo.
   Decisión: 3 intentos con backoff es el estándar.
3. POLLING: Short polling adaptativo → Trade-off: Más peticiones que 
   long polling, pero más simple de implementar y con backoff se mitiga
   la carga. Impacto moderado en batería.
4. OBSERVADORES: 3 observadores → Trade-off: Cada observador añade
   tiempo de ejecución al ciclo si son síncronos. 
   Decisión: Desacopla la lógica completamente.
5. MEJORA FUTURA: Mover observadores a tareas asíncronas para no
   bloquear el ciclo principal del polling.
"""

import asyncio

class Observador:
    def actualizar(self, datos):
        pass

class Observable:
    def __init__(self):
        self._observadores = []
        
    def suscribir(self, observador):
        if observador not in self._observadores:
            self._observadores.append(observador)
            
    def desuscribir(self, observador):
        if observador in self._observadores:
            self._observadores.remove(observador)
            
    def _notificar(self, datos):
        for obs in self._observadores:
            try:
                obs.actualizar(datos)
            except Exception as e:
                print(f"Error en observador: {e}")

class MonitorPedidos(Observable):
    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.ejecutando = False
        self.intervalo_base = 5
        self.intervalo_max = 60
        self.intervalo_actual = self.intervalo_base
        self.ultimo_etag = None
        
    async def _consultar_pedidos(self):
        # Simulación de GET a /pedidos con timeout
        try:
            # Simulando respuesta 200 OK con cambios
            status = 200
            
            if status == 200:
                datos = {
                  "pedidos": [
                    {"id": "P001", "cliente": "Ana", "total": 450.00, "status": "PENDIENTE"},
                    {"id": "P002", "cliente": "Carlos", "total": 120.50, "status": "RETRASADO"}
                  ]
                }
                self.ultimo_etag = "nuevo-etag"
                return status, datos
            elif status == 304:
                return status, None
            elif status >= 500:
                print(f"Error 5xx del servidor")
                return status, None
            elif status >= 400:
                print(f"Error 4xx del cliente")
                return status, None
                
        except asyncio.TimeoutError:
            print("Warning: Timeout al consultar pedidos")
            return 408, None
        except Exception as e:
            print(f"Error de red: {e}")
            return 0, None

    async def iniciar(self):
        self.ejecutando = True
        while self.ejecutando:
            status, datos = await self._consultar_pedidos()
            
            if status == 200 and datos:
                self._notificar(datos)
                self.intervalo_actual = self.intervalo_base
            elif status == 304:
                self.intervalo_actual = min(self.intervalo_actual * 1.5, self.intervalo_max)
            elif status >= 500 or status == 408 or status == 0:
                self.intervalo_actual = min(self.intervalo_actual * 2, self.intervalo_max)
                
            if self.ejecutando:
                await asyncio.sleep(self.intervalo_actual)
                
    def detener(self):
        self.ejecutando = False

class ObservadorPedidosUI(Observador):
    def actualizar(self, datos):
        pedidos = datos.get("pedidos", [])
        print(f"[UI] Hay {len(pedidos)} pedidos actuales:")
        for p in pedidos:
            print(f" - {p['id']}: {p['cliente']} (${p['total']}) [{p['status']}]")

class ObservadorPedidosCriticos(Observador):
    def actualizar(self, datos):
        pedidos = datos.get("pedidos", [])
        retrasados = [p for p in pedidos if p.get("status") == "RETRASADO"]
        for p in retrasados:
            print(f"¡ALERTA! El pedido {p['id']} de {p['cliente']} está RETRASADO.")

async def main():
    monitor = MonitorPedidos("https://api.ecomarket.com")
    monitor.suscribir(ObservadorPedidosUI())
    monitor.suscribir(ObservadorPedidosCriticos())
    
    # Simular ejecución por 6 segundos
    task = asyncio.create_task(monitor.iniciar())
    await asyncio.sleep(6)
    monitor.detener()
    await task

if __name__ == "__main__":
    asyncio.run(main())
