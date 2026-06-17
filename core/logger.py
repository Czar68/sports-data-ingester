import logging
import time
from functools import wraps
import httpx
from typing import Callable, Any

# Configure standard logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ingestion")

def observe_api_call(func: Callable) -> Callable:
    """
    Decorator that captures execution time and status codes for API calls.
    Works for async functions.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        start_time = time.perf_counter()
        status_code = None
        try:
            result = await func(*args, **kwargs)
            if isinstance(result, httpx.Response):
                status_code = result.status_code
            return result
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            raise
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            raise
        finally:
            end_time = time.perf_counter()
            duration = end_time - start_time
            if status_code is not None:
                logger.info(f"API Call '{func.__name__}' completed in {duration:.4f}s with status {status_code}")
            else:
                logger.info(f"API Call '{func.__name__}' completed in {duration:.4f}s")

    return wrapper
