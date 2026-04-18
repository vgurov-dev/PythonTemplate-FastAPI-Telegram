"""Tasks infrastructure package."""
from abc import ABC, abstractmethod
from typing import Any

from celery import Celery
from celery import Task as CeleryTask


class BaseTask(CeleryTask, ABC):
    """Base Celery task."""

    def on_failure(self, exc: Exception, task_id: str, args: tuple, kwargs: dict, einfo: Any) -> None:
        """Handle task failure."""
        pass

    def on_success(self, retval: Any, task_id: str, args: tuple, kwargs: dict) -> None:
        """Handle task success."""
        pass


def create_task(name: str, **kwargs) -> type[BaseTask]:
    """Create Celery task."""

    class Task(BaseTask):
        autoretry_for = (Exception,)
        retry_backoff = True
        retry_backoff_max = 700
        retry_jitter = True

    Task.__name__ = name
    return Task