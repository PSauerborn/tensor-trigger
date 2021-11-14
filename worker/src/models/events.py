"""Module containing event definitions"""

from uuid import UUID
from typing import Union, Dict, List

from pydantic import BaseModel, validator, \
    ValidationError


class ModelRunEvent(BaseModel):

    model_id: UUID
    user: str


class ModelTrainEvent(BaseModel):

    model_id: UUID
    user: str
    epochs: int = 100
    input_vectors: List[Dict[str, float]]
    output_vectors: List[List[float]]


ALLOWED_EVENT_TYPES = {
    'model_run': ModelRunEvent,
    'model_train': ModelTrainEvent
}

class TensorTriggerPayload(BaseModel):

    job_id: UUID
    event_type: str
    event: Union[ModelTrainEvent, ModelRunEvent]

    @validator('event_type')
    def validate_event_type(cls, v):
        if v not in ALLOWED_EVENT_TYPES:
            raise ValueError('Invalid event type ' + v)
        return v

    @validator('event')
    def validate_event(cls, v, values, **kwargs):

        event_cls = ALLOWED_EVENT_TYPES.get(values['event_type'])
        if not isinstance(v, event_cls):
            raise ValueError('Event type mismatch')
        return v


if __name__ == '__main__':

    from uuid import uuid4

    run_event = {
        'model_id': str(uuid4()),
        'job_id': str(uuid4()),
        'user': 'test-user'
    }

    train_event = {
        'model_id': str(uuid4()),
        'job_id': str(uuid4()),
        'user': 'test-user',
        'input_vectors': [
            {
                'test-value': 54
            }
        ]
    }

    payload = {
        'event_type': 'model_t',
        'event': run_event
    }
    e = TensorTriggerPayload(**payload)
    e.validate_event()