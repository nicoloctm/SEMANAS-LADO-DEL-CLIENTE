import time
import random
import functools
import requests

def with_retry(max_retries=3, base_delay=1.0, max_delay=60.0):
    """
    Decorador para reintentar automáticamente funciones que realizan peticiones HTTP.
    Reintenta en caso de errores del servidor (5xx) y timeouts de red.
    Usa retroceso exponencial (exponential backoff) con variación aleatoria (jitter).
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from cliente_ecomarket import ValidationError, AuthenticationError, NotFoundError, ConflictError, ServerError
            
            delay = base_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # 1. Determinar si el error es del cliente (4xx) - NO reintentar
                    if isinstance(e, (ValidationError, AuthenticationError, NotFoundError, ConflictError)):
                        raise e
                    
                    # 2. Determinar si es reintentable
                    is_retryable = False
                    if isinstance(e, ServerError):
                        is_retryable = True
                    elif isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
                        is_retryable = True
                    elif isinstance(e, requests.exceptions.HTTPError):
                        if e.response is not None and e.response.status_code >= 500:
                            is_retryable = True
                    
                    # Si no es reintentable (ej: errores de sintaxis u otras excepciones), propagar de inmediato
                    if not is_retryable:
                        raise e
                    
                    last_exception = e
                    
                    # Si ya estamos en el último intento, no esperar y salir del bucle para lanzar el error
                    if attempt == max_retries:
                        break
                    
                    # 3. Calcular tiempo de espera con Exponential Backoff
                    # delay_backoff = base_delay * 2^attempt
                    current_delay = min(base_delay * (2 ** attempt), max_delay)
                    
                    # 4. Añadir Jitter (variación aleatoria para desincronizar clientes)
                    # Tomamos un valor aleatorio entre 0.8 y 1.2 veces el delay calculado
                    actual_delay = current_delay * random.uniform(0.8, 1.2)
                    
                    print(f"[REINTENTO] Intento {attempt + 1} de {max_retries} falló debido a {type(e).__name__}. "
                          f"Reintentando en {actual_delay:.2f} segundos...")
                    
                    time.sleep(actual_delay)
                    
            # Si se agotaron los intentos, lanzar el último error registrado
            print(f"[REINTENTO] Se agotaron los {max_retries} reintentos.")
            raise last_exception
            
        return wrapper
    return decorator
