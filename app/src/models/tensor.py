"""Module containing data classes for tensor trigger request"""

from typing import Dict, List, Union
from uuid import UUID

from pydantic import BaseModel


class AsyncBatchProcessRequest(BaseModel):

    model_id: UUID
    input_data: str


class BatchProcessRequest(BaseModel):

    model_id: UUID
    input_vectors: List[Dict[str, Union[int, float]]]


class ProcessRequest(BaseModel):

    model_id: UUID
    input_vector: Dict[str, Union[int, float]]