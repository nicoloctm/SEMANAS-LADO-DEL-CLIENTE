"""
RECEPTOR ALERTAS ECOMARKET — Decisiones de arquitectura (cliente)

SSE elegido sobre polling porque:
- Escenario A (10k usuarios, cambios lentos): SSE usa 1 conexión TCP persistente por cliente,
  mientras que polling generaría muchísimas peticiones innecesarias.
- Escenario B (Legacy sin streaming): Polling obligatorio, ya que el servidor no soporta SSE.
- Escenario C (Móvil con caídas 3G): Polling puede ser mejor o SSE con reconexión robusta, 
  pero SSE gasta menos batería al no enviar headers en cada ciclo si la conexión sobrevive.
- Escenario D (Bidireccional en vivo): WebSocket es mejor porque SSE es solo unidireccional.
"""

import asyncio
import httpx

class ReceptorAlertas:
    def __init__(self, url):
        self.url = url
        self.ejecutando = False
        self.ultimo_id = None
        self.retry_ms = 3000
        self.intentos = 0
        self.max_intentos = 5

    async def iniciar(self):
        self.ejecutando = True
        while self.ejecutando and self.intentos < self.max_intentos:
            headers = {"Accept": "text/event-stream"}
            if self.ultimo_id:
                headers["Last-Event-ID"] = str(self.ultimo_id)
            
            try:
                # Simularemos la lectura de un stream
                print(f"[*] Conectando a {self.url} (Intento {self.intentos + 1}) con headers: {headers}")
                await self._simular_stream()
                
            except asyncio.TimeoutError:
                print("[!] Timeout de red.")
                self.intentos += 1
                await asyncio.sleep(self.retry_ms / 1000)
            except Exception as e:
                print(f"[!] Error de conexión: {e}")
                self.intentos += 1
                await asyncio.sleep(self.retry_ms / 1000)
                
        if self.intentos >= self.max_intentos:
            print("[x] Máximo de reconexiones alcanzado. Deteniendo.")
            
    async def _simular_stream(self):
        # Simulamos eventos llegando
        eventos = [
            "id: 1\nevent: precio-actualizado\ndata: {\"producto\":\"A01\",\"precio\":47}\n\n",
            "id: 2\nevent: stock-critico\ndata: {\"producto\":\"B07\",\"stock\":1}\n\n",
            ": ping\n\n",
            "id: 3\nevent: precio-actualizado\ndata: {\"producto\":\"A01\",\"precio\":45}\n\n"
        ]
        
        for evt_str in eventos:
            if not self.ejecutando:
                break
            # Simulando parseo manual
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
                    if evento_tipo == "precio-actualizado":
                        print(f"[PRECIO] Actualizado: {data}")
                    elif evento_tipo == "stock-critico":
                        print(f"⚠️ [ALERTA STOCK] Crítico: {data}")
                    elif evento_tipo is None and not data:
                        # ping
                        pass
                    # Reset buffer vars
                    evento_tipo = None
                    data = ""
            self.intentos = 0 # reset intentos por conexión exitosa
            await asyncio.sleep(1) # Simular tiempo entre eventos
            
        # Simular caída de red después de los eventos
        raise asyncio.TimeoutError("Caída de red simulada")

    def detener(self):
        self.ejecutando = False
        print("[*] Detención limpia solicitada.")

async def main():
    receptor = ReceptorAlertas("https://api.ecomarket.com/alertas")
    task = asyncio.create_task(receptor.iniciar())
    await asyncio.sleep(6) # Dejar que procese y simule reconexión
    receptor.detener()
    await task

if __name__ == "__main__":
    asyncio.run(main())
