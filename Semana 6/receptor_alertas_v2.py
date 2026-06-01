"""
RECEPTOR ALERTAS V2 — Integración de SSE con patrón Observer.
"""
import asyncio

class Observable:
    def __init__(self):
        self._observadores = []
        
    def suscribir(self, observador):
        if observador not in self._observadores:
            self._observadores.append(observador)
            
    def desuscribir(self, observador):
        if observador in self._observadores:
            self._observadores.remove(observador)
            
    def _notificar(self, evento_tipo, data):
        for obs in self._observadores:
            # En esta versión delegamos a que cada observador filtre internamente o actúe según el tipo.
            try:
                obs.actualizar(evento_tipo, data)
            except Exception as e:
                print(f"Error en observador {obs.__class__.__name__}: {e}")

class ReceptorAlertasV2(Observable):
    """
    Decidí usar HERENCIA (ReceptorAlertasV2 hereda de Observable) en lugar de composición,
    porque conceptualmente el Receptor ES la fuente de datos (Observable) que notifica
    al resto de la aplicación sobre los eventos que recibe del servidor.
    """
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.ejecutando = False
        self.ultimo_id = None
        self.retry_ms = 3000
        self.intentos = 0
        self.max_intentos = 5

    async def iniciar(self):
        self.ejecutando = True
        while self.ejecutando and self.intentos < self.max_intentos:
            try:
                print(f"[*] Conectando a {self.url} (Intento {self.intentos + 1})")
                await self._simular_stream()
            except asyncio.TimeoutError:
                self.intentos += 1
                await asyncio.sleep(self.retry_ms / 1000)
            except Exception:
                self.intentos += 1
                await asyncio.sleep(self.retry_ms / 1000)
                
    async def _simular_stream(self):
        eventos = [
            "id: 1\nevent: precio-actualizado\ndata: {\"producto\":\"A01\",\"precio\":47}\n\n",
            "id: 2\nevent: stock-critico\ndata: {\"producto\":\"B07\",\"stock\":1}\n\n",
            "id: 3\nevent: otro-evento\ndata: {}\n\n"
        ]
        
        for evt_str in eventos:
            if not self.ejecutando:
                break
            
            lineas = evt_str.split("\n")
            evento_tipo = None
            data = ""
            for linea in lineas:
                if linea.startswith("id: "):
                    self.ultimo_id = linea[4:].strip()
                elif linea.startswith("event: "):
                    evento_tipo = linea[7:].strip()
                elif linea.startswith("data: "):
                    data = linea[6:].strip()
                elif linea == "": # fin de mensaje
                    # ¡AQUÍ ESTÁ LA INTEGRACIÓN CON OBSERVER!
                    if evento_tipo:
                        self._notificar(evento_tipo, data)
                        
                    evento_tipo = None
                    data = ""
            self.intentos = 0
            await asyncio.sleep(1)
        raise asyncio.TimeoutError()

    def detener(self):
        self.ejecutando = False

# Suscriptores independientes
class ActualizadorPreciosUI:
    def actualizar(self, tipo, data):
        if tipo == "precio-actualizado":
            print(f"[UI Precios] Tabla actualizada con: {data}")

class AlertaStockCritico:
    def actualizar(self, tipo, data):
        if tipo == "stock-critico":
            print(f"[ALERTA URGENTE] Stock crítico detectado: {data}")

class RegistradorAuditoria:
    def actualizar(self, tipo, data):
        print(f"[AUDITORIA] Registrando evento '{tipo}' -> Datos: {data}")

async def main():
    receptor = ReceptorAlertasV2("https://api.ecomarket.com/alertas")
    
    # Inscribir los observadores
    receptor.suscribir(ActualizadorPreciosUI())
    receptor.suscribir(AlertaStockCritico())
    receptor.suscribir(RegistradorAuditoria())
    
    task = asyncio.create_task(receptor.iniciar())
    await asyncio.sleep(4)
    receptor.detener()
    await task

if __name__ == "__main__":
    asyncio.run(main())
