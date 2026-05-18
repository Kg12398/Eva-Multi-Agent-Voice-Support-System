"""
Circuit breaker pattern for external API fault tolerance.
Prevents cascading failures when Deepgram, Gemini, or TTS services go down.
"""

import asyncio
import time
from typing import Callable, Any, Optional
from enum import Enum
from app.utils.logger import CallLogger


class CircuitState(str, Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Service is down, reject calls
    HALF_OPEN = "half_open" # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker for external API calls.
    
    Usage:
        breaker = CircuitBreaker("deepgram_stt", failure_threshold=3)
        result = await breaker.call(deepgram_transcribe, audio_data)
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout_seconds: int = 30,
        timeout_ms: int = 5000,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout_seconds
        self.timeout_ms = timeout_ms
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.logger = CallLogger(call_id=f"circuit:{name}")

    async def call(
        self,
        func: Callable,
        *args,
        fallback: Optional[Callable] = None,
        **kwargs,
    ) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: The async function to call
            fallback: Optional fallback function if circuit is open
        """
        # Check if circuit should transition from OPEN to HALF_OPEN
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.logger.info("Circuit half-open, testing recovery")
            else:
                self.logger.warning("Circuit OPEN, using fallback")
                if fallback:
                    return await fallback(*args, **kwargs)
                raise CircuitOpenError(f"Circuit breaker {self.name} is OPEN")

        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.timeout_ms / 1000,
            )

            # Success — reset failure count
            if self.state == CircuitState.HALF_OPEN:
                self.logger.info("Circuit recovered, closing")
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            return result

        except asyncio.TimeoutError:
            self._record_failure(f"Timeout after {self.timeout_ms}ms")
            if fallback:
                return await fallback(*args, **kwargs)
            raise

        except Exception as e:
            self._record_failure(str(e))
            if fallback:
                return await fallback(*args, **kwargs)
            raise

    def _record_failure(self, reason: str):
        """Record a failure and potentially open the circuit."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.logger.warning(
            f"Failure #{self.failure_count}/{self.failure_threshold}: {reason}"
        )

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.logger.error(f"Circuit OPENED after {self.failure_count} failures")

    @property
    def is_available(self) -> bool:
        """Check if the circuit is available for calls."""
        return self.state != CircuitState.OPEN


class CircuitOpenError(Exception):
    """Raised when a circuit breaker is in the OPEN state."""
    pass
