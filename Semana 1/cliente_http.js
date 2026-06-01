/**
 * =========================================================================
 * CLIENTE HTTP DE ECOMARKET (cliente_http.js)
 * =========================================================================
 * Asignatura: Programación Distribuida del Lado del Cliente (UAN)
 * Modelo: AETL (Fases Aplica, Valida y Profundiza)
 * 
 * Este archivo implementa un cliente HTTP asíncrono y resiliente utilizando
 * la API Fetch nativa. Incorpora:
 *   1. Peticiones GET y POST con tipado y cabeceras de negociación.
 *   2. Resiliencia: Control de Timeouts y reintentos automáticos en 5xx/red.
 *   3. Seguridad y Validación: Validación de Content-Type y enmascaramiento de tokens.
 *   4. Observabilidad: Capa de Logging por niveles (DEBUG, INFO, WARN, ERROR).
 *   5. Simulador integrado de Caos/Mock para pruebas fuera de línea.
 * =========================================================================
 */

// =========================================================================
// CONFIGURACIÓN CENTRALIZADA
// =========================================================================
const CONFIG = {
    BASE_URL: 'https://api.ecomarket.com/api',
    TIMEOUT_MS: 3000,              // Timeout de 3 segundos para prevenir bloqueos
    CLIENT_VERSION: '1.0',         // Cabecera X-Client-Version
    AUTH_TOKEN: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjQyLCJyb2xlIjoicHJvZHVjdG9yIn0.signature',
    MAX_RETRIES: 3,                // Intentos máximos de reconexión para fallos transitorios
    RETRY_DELAY_MS: 1000,          // Espera entre reintentos
    USE_MOCK_SIMULATOR: true       // Activar el simulador interno para pruebas y caos
};

// =========================================================================
// CAPA DE OBSERVABILIDAD: LOGGER PROFESIONAL
// =========================================================================
const LOG_LEVELS = { DEBUG: 0, INFO: 1, WARN: 2, ERROR: 3 };
const CURRENT_LOG_LEVEL = LOG_LEVELS.DEBUG;

class Logger {
    static _format(level, message, meta = {}) {
        const timestamp = new Date().toISOString();
        // Enmascarar tokens de autorización si se incluyen en los metadatos
        const sanitizedMeta = { ...meta };
        if (sanitizedMeta.headers && sanitizedMeta.headers['Authorization']) {
            sanitizedMeta.headers = { ...sanitizedMeta.headers };
            sanitizedMeta.headers['Authorization'] = 'Bearer *****[REDACTED]*****';
        }
        
        const metaStr = Object.keys(sanitizedMeta).length ? ` | Meta: ${JSON.stringify(sanitizedMeta)}` : '';
        return `[${timestamp}] [${level}] ${message}${metaStr}`;
    }

    static debug(message, meta) {
        if (CURRENT_LOG_LEVEL <= LOG_LEVELS.DEBUG) {
            console.log('\x1b[36m%s\x1b[0m', this._format('DEBUG', message, meta));
        }
    }

    static info(message, meta) {
        if (CURRENT_LOG_LEVEL <= LOG_LEVELS.INFO) {
            console.log('\x1b[32m%s\x1b[0m', this._format('INFO', message, meta));
        }
    }

    static warn(message, meta) {
        if (CURRENT_LOG_LEVEL <= LOG_LEVELS.WARN) {
            console.log('\x1b[33m%s\x1b[0m', this._format('WARN', message, meta));
        }
    }

    static error(message, meta) {
        if (CURRENT_LOG_LEVEL <= LOG_LEVELS.ERROR) {
            console.error('\x1b[31m%s\x1b[0m', this._format('ERROR', message, meta));
        }
    }
}

// =========================================================================
// MOTOR DE PETICIONES HTTP CON CONTROL DE RESILIENCIA Y CAOS
// =========================================================================

/**
 * Realiza una petición HTTP utilizando fetch con control de timeout y reintentos.
 * @param {string} path Ruta relativa a la URL base.
 * @param {object} options Opciones de la petición.
 * @param {number} attempt Intento actual (usado para reintentos recursivos).
 */
async function apiRequest(path, options = {}, attempt = 1) {
    const url = `${CONFIG.BASE_URL}${path}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), CONFIG.TIMEOUT_MS);
    
    // Inyectar cabeceras requeridas y de negociación
    const requestHeaders = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-Client-Version': CONFIG.CLIENT_VERSION,
        ...options.headers
    };

    if (CONFIG.AUTH_TOKEN) {
        requestHeaders['Authorization'] = `Bearer ${CONFIG.AUTH_TOKEN}`;
    }

    const fetchOptions = {
        ...options,
        headers: requestHeaders,
        signal: controller.signal
    };

    const startTime = Date.now();
    Logger.debug(`Iniciando petición ${options.method || 'GET'} a ${path} (Intento ${attempt}/${CONFIG.MAX_RETRIES})`, {
        headers: requestHeaders,
        body: options.body ? JSON.parse(options.body) : null
    });

    try {
        // Ejecutar a través del simulador o del fetch nativo
        const response = CONFIG.USE_MOCK_SIMULATOR 
            ? await mockFetch(url, fetchOptions)
            : await fetch(url, fetchOptions);

        clearTimeout(timeoutId);
        const duration = Date.now() - startTime;
        const contentType = response.headers.get('content-type') || '';

        // 1. Auditoría del Código de Estado HTTP (Contrato semántico)
        if (!response.ok) {
            // Si es un error transitorio de servidor (5xx) o de red, intentamos de nuevo si quedan intentos
            if (response.status >= 500 && attempt < CONFIG.MAX_RETRIES) {
                Logger.warn(`Error del servidor (${response.status}) en ${path}. Reintentando en ${CONFIG.RETRY_DELAY_MS}ms...`, { duration });
                await delay(CONFIG.RETRY_DELAY_MS);
                return await apiRequest(path, options, attempt + 1);
            }
            
            // Si es un error 4xx (problema del cliente), NO reintentamos. Es inútil según las reglas HTTP.
            let errorBody = {};
            if (contentType.includes('application/json')) {
                errorBody = await response.json();
            } else {
                errorBody = { mensaje: await response.text() };
            }
            
            const errorMsg = errorBody.mensaje || `Error de red con código ${response.status}`;
            throw { status: response.status, mensaje: errorMsg, path };
        }

        // 2. Validación crítica de formato de respuesta (Content-Type)
        if (!contentType.includes('application/json')) {
            throw { status: 422, mensaje: `Respuesta del servidor no es JSON. Se recibió: ${contentType}`, path };
        }

        const data = await response.json();
        const sizeBytes = JSON.stringify(data).length; // Estimación rápida
        Logger.info(`Petición ${options.method || 'GET'} exitosa a ${path}`, {
            status: response.status,
            durationMs: duration,
            sizeBytes
        });
        
        return data;

    } catch (error) {
        clearTimeout(timeoutId);
        const duration = Date.now() - startTime;

        // Clasificar error de AbortController (Timeout)
        if (error.name === 'AbortError') {
            Logger.error(`Timeout excedido (${CONFIG.TIMEOUT_MS}ms) al conectar con ${path}`, { duration });
            if (attempt < CONFIG.MAX_RETRIES) {
                Logger.warn(`Reintentando tras timeout en ${path}...`, { attempt });
                await delay(CONFIG.RETRY_DELAY_MS);
                return await apiRequest(path, options, attempt + 1);
            }
            throw { status: 408, mensaje: `El servidor tardó demasiado en responder (> ${CONFIG.TIMEOUT_MS}ms)`, path };
        }

        // Si ya es un error estructurado, lo propagamos
        if (error.status) {
            Logger.error(`Error HTTP ${error.status} en ${path}: ${error.mensaje}`, { duration });
            throw error;
        }

        // Error genérico de red (p. ej. sin internet)
        Logger.error(`Fallo de conexión de red al conectar con ${path}`, { originalError: error.message, duration });
        if (attempt < CONFIG.MAX_RETRIES) {
            Logger.warn(`Reintentando tras error de red en ${path}...`, { attempt });
            await delay(CONFIG.RETRY_DELAY_MS);
            return await apiRequest(path, options, attempt + 1);
        }
        throw { status: 503, mensaje: 'El servicio no está disponible temporalmente. Comprueba tu conexión de red.', path };
    }
}

// Helper para delay de reintentos
function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// =========================================================================
// INTERFAZ PÚBLICA DEL CLIENTE (APIs del Catálogo EcoMarket)
// =========================================================================

/**
 * Obtener todos los productos filtrados
 * @param {object} filtros Filtros opcionales (categoria, productor_id, page, limit)
 */
async function obtenerProductos(filtros = {}) {
    const params = new URLSearchParams();
    Object.entries(filtros).forEach(([key, val]) => {
        if (val !== undefined && val !== null) {
            params.append(key, val);
        }
    });
    const queryString = params.toString() ? `?${params.toString()}` : '';
    return await apiRequest(`/productos${queryString}`, { method: 'GET' });
}

/**
 * Obtener un producto por su identificador único
 * @param {number} id ID del producto
 */
async function obtenerProductoPorId(id) {
    if (!Number.isInteger(id)) {
        throw { status: 400, mensaje: 'El ID del producto debe ser un número entero válido.' };
    }
    return await apiRequest(`/productos/${id}`, { method: 'GET' });
}

/**
 * Registrar un nuevo producto en EcoMarket
 * @param {object} producto Datos del producto según el esquema ProductoInput
 */
async function crearProducto(producto) {
    // Validación básica del lado del cliente antes de enviar (evitar peticiones innecesarias)
    if (!producto.nombre || producto.nombre.length < 3) {
        throw { status: 400, mensaje: 'El nombre del producto es obligatorio y debe tener al menos 3 caracteres.' };
    }
    if (typeof producto.precio !== 'number' || producto.precio <= 0) {
        throw { status: 400, mensaje: 'El precio debe ser un número positivo.' };
    }

    return await apiRequest('/productos', {
        method: 'POST',
        body: JSON.stringify(producto)
    });
}


// =========================================================================
// SIMULADOR DE MOCK SERVER Y ESCENARIOS DE CAOS (Para demostración)
// =========================================================================

// Base de datos simulada en memoria
const BD_SIMULADA = [
    { id: 1, nombre: 'Miel de Abeja Silvestre', precio: 120.50, categoria: 'miel', productor_id: 42, disponible: true, creado_en: '2026-05-20T10:00:00Z' },
    { id: 2, nombre: 'Jitomate Saladet Orgánico (kg)', precio: 45.00, categoria: 'verduras', productor_id: 15, disponible: true, creado_en: '2026-05-21T08:30:00Z' },
    { id: 3, nombre: 'Mermelada de Fresa Casera', precio: 80.00, categoria: 'conservas', productor_id: 42, disponible: false, creado_en: '2026-05-19T14:22:00Z' }
];

// Variable global para configurar fallas simuladas
let escenarioCaosActivo = null;
let contadorPeticionesSimuladas = 0;

async function mockFetch(url, options) {
    contadorPeticionesSimuladas++;
    
    // Inyectar retardo básico de red de 200ms
    await delay(200);

    // 1. Simulación de Caos: Red Lenta / Latencia Extrema
    if (escenarioCaosActivo === 'RED_LENTA') {
        Logger.warn('[SIMULADOR DE CAOS] Aplicando retraso de red extrema de 4000ms (excede el timeout)...');
        await delay(4000); 
    }

    // 2. Simulación de Caos: Servidor Intermitente (Falla cada 2 peticiones y revive en la 3era)
    if (escenarioCaosActivo === 'SERVIDOR_INTERMITENTE') {
        if (contadorPeticionesSimuladas % 3 !== 0) {
            Logger.warn(`[SIMULADOR DE CAOS] Fallo intermitente simulado (Petición #${contadorPeticionesSimuladas}). Código 503.`);
            return {
                ok: false,
                status: 503,
                headers: new Map([['content-type', 'application/json']]),
                json: async () => ({ codigo: 'SERVICE_UNAVAILABLE', mensaje: 'Servidor sobrecargado temporalmente.' })
            };
        } else {
            Logger.info(`[SIMULADOR DE CAOS] Petición #${contadorPeticionesSimuladas} exitosa (El reintento funcionó).`);
        }
    }

    // 3. Simulación de Caos: Respuesta con formato inesperado (HTML en lugar de JSON)
    if (escenarioCaosActivo === 'RESPUESTA_HTML') {
        Logger.warn('[SIMULADOR DE CAOS] Enviando respuesta errónea en formato HTML en vez de JSON.');
        return {
            ok: true,
            status: 200,
            headers: new Map([['content-type', 'text/html; charset=utf-8']]),
            text: async () => '<html><body><h1>502 Bad Gateway</h1></body></html>'
        };
    }

    // 4. Simulación de Caos: Timeout del Servidor (Tarda 60 segundos)
    if (escenarioCaosActivo === 'TIMEOUT_60S') {
        Logger.warn('[SIMULADOR DE CAOS] Servidor colgado. Simulación de respuesta tras 10 segundos...');
        await delay(10000);
    }

    // --- PROCESAMIENTO ESTÁNDAR DEL MOCK SERVER ---
    const parsedUrl = new URL(url);
    const path = parsedUrl.pathname.replace('/api', '');
    const method = options.method || 'GET';

    // RUTA: GET /productos
    if (path.startsWith('/productos') && method === 'GET') {
        // Comprobar si es un producto específico /productos/{id}
        const match = path.match(/^\/productos\/(\d+)$/);
        if (match) {
            const id = parseInt(match[1]);
            const producto = BD_SIMULADA.find(p => p.id === id);
            
            // Simular caso 404 (No existe)
            if (!producto) {
                return {
                    ok: false,
                    status: 404,
                    headers: new Map([['content-type', 'application/json']]),
                    json: async () => ({ codigo: 'NOT_FOUND', mensaje: `El producto con ID ${id} no existe.` })
                };
            }

            return {
                ok: true,
                status: 200,
                headers: new Map([['content-type', 'application/json']]),
                json: async () => producto
            };
        }

        // Listado de productos con filtros
        const categoria = parsedUrl.searchParams.get('categoria');
        const productor_id = parsedUrl.searchParams.get('productor_id');
        let dataFiltered = [...BD_SIMULADA];

        if (categoria) {
            dataFiltered = dataFiltered.filter(p => p.categoria === categoria);
        }
        if (productor_id) {
            dataFiltered = dataFiltered.filter(p => p.productor_id === parseInt(productor_id));
        }

        return {
            ok: true,
            status: 200,
            headers: new Map([['content-type', 'application/json']]),
            json: async () => ({
                total: dataFiltered.length,
                page: 1,
                limit: 10,
                data: dataFiltered
            })
        };
    }

    // RUTA: POST /productos
    if (path === '/productos' && method === 'POST') {
        // Validar token de autenticación
        const authHeader = options.headers['Authorization'] || '';
        if (!authHeader.startsWith('Bearer eyJhbGci')) {
            return {
                ok: false,
                status: 401,
                headers: new Map([['content-type', 'application/json']]),
                json: async () => ({ codigo: 'UNAUTHORIZED', mensaje: 'Sesión inválida o expirada.' })
            };
        }

        const body = JSON.parse(options.body);

        // Validación de SKU duplicado simulado
        if (body.nombre === 'SKU_DUPLICADO') {
            return {
                ok: false,
                status: 409,
                headers: new Map([['content-type', 'application/json']]),
                json: async () => ({ codigo: 'CONFLICT', mensaje: 'El producto con este SKU/Nombre ya existe en el catálogo.' })
            };
        }

        const nuevoProducto = {
            id: BD_SIMULADA.length + 1,
            ...body,
            creado_en: new Date().toISOString()
        };
        BD_SIMULADA.push(nuevoProducto);

        return {
            ok: true,
            status: 201,
            headers: new Map([['content-type', 'application/json']]),
            json: async () => nuevoProducto
        };
    }

    // Si llega aquí, es una ruta no mapeada
    return {
        ok: false,
        status: 404,
        headers: new Map([['content-type', 'application/json']]),
        json: async () => ({ codigo: 'NOT_FOUND', mensaje: 'Endpoint no encontrado.' })
    };
}


// =========================================================================
// RUNNER: DEMOSTRACIÓN PRÁCTICA Y PRUEBAS DE CAOS
// =========================================================================
async function ejecutarDemostracion() {
    console.log('\n\x1b[35m=========================================================================');
    console.log(' INICIANDO RUNNER DE PRUEBAS DEL CLIENTE HTTP (EcoMarket)');
    console.log('=========================================================================\x1b[0m\n');

    // ---------------------------------------------------------------------
    // CASO 1: Camino Feliz (Happy Path) - GET /productos
    // ---------------------------------------------------------------------
    console.log('\n--- CASO 1: OBTENER PRODUCTOS (Happy Path) ---');
    escenarioCaosActivo = null;
    try {
        const catalogo = await obtenerProductos({ categoria: 'miel' });
        console.log(`\x1b[32m✔ Catálogo obtenido. Total: ${catalogo.total} productos.\x1b[0m`);
    } catch (e) {
        console.error('❌ Falló la petición:', e);
    }

    // ---------------------------------------------------------------------
    // CASO 2: Error Semántico 404 - GET /productos/999
    // ---------------------------------------------------------------------
    console.log('\n--- CASO 2: OBTENER PRODUCTO NO EXISTENTE (404 Not Found) ---');
    try {
        await obtenerProductoPorId(999);
    } catch (e) {
        console.log(`\x1b[32m✔ Control exitoso de 404. Código: ${e.status}. Mensaje: "${e.mensaje}"\x1b[0m`);
    }

    // ---------------------------------------------------------------------
    // CASO 3: Registro exitoso - POST /productos
    // ---------------------------------------------------------------------
    console.log('\n--- CASO 3: CREACIÓN DE PRODUCTO (201 Created) ---');
    try {
        const nuevo = await crearProducto({
            nombre: 'Queso Crema Orgánico',
            precio: 65.50,
            categoria: 'lacteos',
            productor_id: 42,
            disponible: true
        });
        console.log(`\x1b[32m✔ Producto registrado con éxito. ID asignado: ${nuevo.id}\x1b[0m`);
    } catch (e) {
        console.error('❌ Error creando producto:', e);
    }

    // ---------------------------------------------------------------------
    // PRUEBAS DE CAOS (Reto 8)
    // ---------------------------------------------------------------------
    console.log('\n\x1b[35m=========================================================================');
    console.log(' SIMULACIÓN DE PRUEBAS DE CAOS (Valida y robustez)');
    console.log('=========================================================================\x1b[0m\n');

    // Escenario A: Servidor Intermitente (503)
    console.log('--- ESCENARIO CAOS A: SERVIDOR INTERMITENTE (Falla de red temporal) ---');
    console.log('Nota: El cliente debería fallar los primeros intentos y triunfar en el 3ero gracias al reintento automático.');
    escenarioCaosActivo = 'SERVIDOR_INTERMITENTE';
    contadorPeticionesSimuladas = 0; // Reiniciar contador
    try {
        const producto = await obtenerProductoPorId(1);
        console.log(`\x1b[32m✔ ¡Recuperado con éxito tras reintentos! Producto: "${producto.nombre}"\x1b[0m`);
    } catch (e) {
        console.error('❌ Error persistente tras reintentos:', e);
    }

    // Escenario B: Timeout de Red (AbortController)
    console.log('\n--- ESCENARIO CAOS B: RED LENTA EXTREMA (Timeout superado) ---');
    console.log(`Nota: Cada intento tardará 4000ms, abortando a los ${CONFIG.TIMEOUT_MS}ms. Se probarán ${CONFIG.MAX_RETRIES} intentos.`);
    escenarioCaosActivo = 'RED_LENTA';
    try {
        await obtenerProductos();
    } catch (e) {
        console.log(`\x1b[32m✔ Timeout controlado correctamente. Código: ${e.status}. Mensaje: "${e.mensaje}"\x1b[0m`);
    }

    // Escenario C: Content-Type incorrecto (Recibe HTML en lugar de JSON)
    console.log('\n--- ESCENARIO CAOS C: RESPUESTA HTML INESPERADA (422 Unprocessable) ---');
    escenarioCaosActivo = 'RESPUESTA_HTML';
    try {
        await obtenerProductos();
    } catch (e) {
        console.log(`\x1b[32m✔ Rechazo de respuesta no-JSON controlado. Código: ${e.status}. Mensaje: "${e.mensaje}"\x1b[0m`);
    }

    console.log('\n\x1b[35m=========================================================================');
    console.log(' RUNNER COMPLETADO DE MANERA EXITOSA');
    console.log('=========================================================================\x1b[0m\n');
}

// Exportar módulos por si se usan en test externos
module.exports = {
    CONFIG,
    obtenerProductos,
    obtenerProductoPorId,
    crearProducto,
    Logger
};

// Auto-ejecutar si se corre directamente
if (require.main === module) {
    ejecutarDemostracion();
}
