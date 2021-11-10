"""Module containing data classes for tensor trigger request"""

from typing import Dict, List

from pydantic import BaseModel, validator

from src.logic.tensor import ALLOWED_TYPES


class SchemaItem(BaseModel):

    var_type: str
    index: int

    @validator('var_type')
    def validate_schema_item(cls, v):
        if v.upper() not in ALLOWED_TYPES:
            raise ValueError('Invalid variable type ' + v)
        return v


class ModelUploadRequest(BaseModel):

    model_schema: Dict[str, SchemaItem]
    model_name: str
    model_description: str
    model_content: str
