"""Module containing data classes for tensor trigger request"""

from typing import Dict, Literal

from pydantic import BaseModel, validator

from src.logic.tensor import ALLOWED_TYPES


class SchemaItem(BaseModel):

    var_type: Literal['INT', 'FLOAT']
    index: int


class ModelSchema(BaseModel):

    input_schema: Dict[str, SchemaItem]
    output_schema: Dict[str, SchemaItem]


class ModelUploadRequest(BaseModel):

    model_schema: ModelSchema
    model_name: str
    model_description: str
    model_content: str
