import time
import logging
from functools import wraps
from typing import Callable, Any
import random

logger = logging.getLogger(__name__)

def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
    """Decorator for retrying functions with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay between retries
        max_delay: Maximum delay between retries
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries:
                        logger.error(f"Function {func.__name__} failed after {max_retries} retries: {str(e)}")
                        raise
                    
                    # Calculate delay with exponential backoff and jitter
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = random.uniform(0, delay * 0.1)  # Add up to 10% jitter
                    total_delay = delay + jitter
                    
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. Retrying in {total_delay:.2f}s...")
                    time.sleep(total_delay)
            
            return None
        return wrapper
    return decorator

def rate_limiter(calls: int = 1, period: float = 1.0):
    """Decorator for rate limiting function calls
    
    Args:
        calls: Number of calls allowed
        period: Time period in seconds
    """
    def decorator(func: Callable) -> Callable:
        last_called = [0.0]
        
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_time = time.time()
            time_since_last = current_time - last_called[0]
            
            if time_since_last < period:
                sleep_time = period - time_since_last
                logger.debug(f"Rate limiting {func.__name__}: sleeping for {sleep_time:.2f}s")
                time.sleep(sleep_time)
            
            last_called[0] = time.time()
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

class FileManager:
    """Utility class for file operations"""
    
    @staticmethod
    def load_text(filepath: str) -> str:
        """Load text from file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    
    @staticmethod
    def save_text(content: str, filepath: str) -> None:
        """Save text to file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

# Create global instance
file_manager = FileManager() 