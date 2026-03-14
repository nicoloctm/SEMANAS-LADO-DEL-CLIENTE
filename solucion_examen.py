import asyncio
import aiohttp
import time
from datetime import datetime

# Configuracion
BASE_URL = "http://ecomarket.local/api/v1"
TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..." # token de prueba
INTERVALO_BASE = 5
INTERVALO_MAX = 60
TIMEOUT = 10

# Clase observador, casi interfaz
class Observador:
    async def actualizar(self, inventario):
        pass

class ModuloCompras(Observador):
    async def actualizar(self, inventario):
        # lógica del modulo de compras
        print("\n--- MODULO DE COMPRAS ---")
        try:
            prods = inventario.get("productos", [])
            for p in prods:
                estatus = p.get("status", "")
                if estatus == "BAJO_MINIMO":
                    # print("Oye!! El producto", p['nombre'], "ID:", p['id'], "tiene", p['stock'])
                    print(f"Oye!! El producto {p['nombre']} (ID: {p['id']}) ya tiene muy poco stock: {p['stock']}")
        except Exception as e:
            print("uff error modulo compras", e)

class ModuloAlertas(Observador):
    async def actualizar(self, inventario):
        print("\n*** MODULO DE ALERTAS ***")
        if "productos" not in inventario or inventario["productos"] is None:
            return
            
        for prod in inventario["productos"]:
            if prod.get("status") == "BAJO_MINIMO":
                url_alerta = BASE_URL + "/alertas"
                mis_headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
                
                # datos json
                data = {
                    "producto_id": prod["id"],
                    "stock_actual": prod["stock"],
                    "stock_minimo": prod["stock_minimo"],
                    # obteniendo la fecha actual
                    "timestamp": datetime.now().isoformat() + "Z"
                }
                
                try:
                    # Abriendo una nueva sesion para el request
                    async with aiohttp.ClientSession() as la_sesion:
                        async with la_sesion.post(url_alerta, headers=mis_headers, json=data) as resp:
                            if resp.status == 201:
                                print(f"-> Alerta mandada exitosamente para el ID {prod['id']}")
                            elif resp.status == 422:
                                print("-> Faltan campos. No se reintenta.")
                            else:
                                print(f"-> Paso algo raro al hacer post: {resp.status}")
                except Exception as ex:
                    print("Error de red en el modulo de alertas:", ex)

# Clase principal
class MonitorInventario:
    def __init__(self):
        self._observadores = []
        self._ultimo_etag = None
        self._ultimo_estado = None
        self._ejecutando = False
        self._intervalo = INTERVALO_BASE
        
        # contador de errores 304 para el backoff
        self.errores_304 = 0

    def suscribir(self, obs):
        self._observadores.append(obs)

    def desuscribir(self, obs):
        self._observadores.remove(obs)
        
    async def _notificar(self, inventario):
        # manejo de errores al notificar observadores
        for obj in self._observadores:
            try:
                await obj.actualizar(inventario)
            except Exception as e:
                print("Fallo en un observador:", e)

    async def _consultar_inventario(self):
        la_url = BASE_URL + "/inventario"
        cabeceras = {
            "Authorization": "Bearer " + TOKEN,
            "Accept": "application/json"
        }
        
        if self._ultimo_etag != None:
            cabeceras["If-None-Match"] = self._ultimo_etag
            
        try:
            tiempo_maximo = aiohttp.ClientTimeout(total=TIMEOUT)
            async with aiohttp.ClientSession(timeout=tiempo_maximo) as session:
                async with session.get(la_url, headers=cabeceras) as la_resp:
                    codigo = la_resp.status
                    
                    if codigo == 200:
                        los_datos = await la_resp.json()
                        etag_nuevo = la_resp.headers.get("ETag")
                        self._ultimo_etag = etag_nuevo
                        self._ultimo_estado = los_datos
                        self._intervalo = INTERVALO_BASE # reseteamos como pide
                        self.errores_304 = 0
                        return los_datos
                        
                    elif codigo == 304:
                        # mismo estatus
                        print("304 - Sigue igual el asunto")
                        self.errores_304 = self.errores_304 + 1
                        return None
                        
                    elif codigo >= 400 and codigo < 500:
                        print("Error del lado cliente:", codigo)
                        # no reintenta, retorno none y no se modifica el intervalo
                        return None 
                        
                    elif codigo >= 500:
                        print("Error del lado del servidor", codigo)
                        # aplicando backoff para errores 5xx
                        self._intervalo = self._intervalo * 2
                        if self._intervalo > INTERVALO_MAX:
                            self._intervalo = INTERVALO_MAX
                        return None
                        
        except asyncio.TimeoutError:
            print("Se acabo el tiempo y no respondio (Timeout)")
            return None
        except aiohttp.ClientError as mi_error_de_red:
            print("Problema de conexion o red:", mi_error_de_red)
            return None
        except Exception as error_desc:
            print("Excepcion no esperada:", error_desc)
            return None

    async def iniciar(self):
        self._ejecutando = True
        print("-- Encendiendo el monitor de inventarios --")
        while self._ejecutando == True:
            el_nuevo = await self._consultar_inventario()
            
            if el_nuevo is not None:
                # valido tantito el json
                if "productos" in el_nuevo and el_nuevo["productos"] is not None:
                    await self._notificar(el_nuevo)
                else:
                    print("El json no contiene productos")
            else:
                # backoff extra si hay demasiados 304
                if self.errores_304 > 5:
                    self._intervalo = self._intervalo + int(self._intervalo / 2)
                    if self._intervalo > INTERVALO_MAX:
                        self._intervalo = INTERVALO_MAX
            
            print(f"Esperando {self._intervalo} segundos...")
            await asyncio.sleep(self._intervalo)
            
    def detener(self):
        print("-- Apagando el monitor... --")
        self._ejecutando = False


async def iniciar_todo():
    # mi monitor
    monitor = MonitorInventario()
    
    # le meto los modulos
    mod_compras = ModuloCompras()
    mod_alertas = ModuloAlertas()
    monitor.suscribir(mod_compras)
    monitor.suscribir(mod_alertas)
    
    # arranco
    la_tarea = asyncio.create_task(monitor.iniciar())
    
    # lo dejo correr un ratillo
    await asyncio.sleep(15)
    
    # deteniendo para que el loop termine correctamente
    monitor.detener()
    await la_tarea

if __name__ == "__main__":
    print("------------------------------------------")
    print("ESTUDIANTE: Angel Adriel Soria Macias")
    print("MATERIA: Programación Distribuida del Lado del Cliente")
    print("MATRICULA: 23207443")
    print("------------------------------------------")
    
    try:
        asyncio.run(iniciar_todo())
    except KeyboardInterrupt:
        print("Cancelado por el usuario")
