"""Module containing data classes for tensor trigger request"""

from typing import Dict, List, Union
from uuid import UUID

from pydantic import BaseModel


class AsyncBatchProcessRequest(BaseModel):

    model_id: UUID
    input_data: str


class BatchProcessRequest(BaseModel):

    model_id: UUID
    input_vectors: List[Dict[str, float]]


class ProcessRequest(BaseModel):

    model_id: UUID
    input_vector: Dict[str, float]


class TrainModelRequest(BaseModel):

    model_id: UUID
    epochs: int = 100
    input_vectors: List[Dict[str, float]]
    output_vectors: List[List[float]]