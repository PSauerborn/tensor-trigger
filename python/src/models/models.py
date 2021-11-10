"""Module containing data classes for tensor trigger request"""

from typing import Dict, List

from pydantic import BaseModel, validator

from src.logic.tensor import is_valid_model_schema


class ModelUploadRequest(BaseModel):

    model_schema: Dict[str, str]
    model_name: str
    model_description: str
    model_content: str

    @validator('model_schema')
    def validate_schema(cls, v):
        if not is_valid_model_schema(v):
            raise ValueError('Invalid model schema')
        return v
