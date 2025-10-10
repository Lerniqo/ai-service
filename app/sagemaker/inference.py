"""Backwards compatible entrypoint for the SageMaker runtime.

Historically the project exposed a standalone FastAPI application dedicated to
SageMaker. Now the same FastAPI application defined in ``app.main`` powers both
SageMaker inference traffic and the public API Gateway. This module simply
re-exports that shared application object so existing tooling that imports
``app.sagemaker.inference`` continues to work.
"""

from app.main import app as sagemaker_app  # noqa: F401

__all__ = ["sagemaker_app"]
