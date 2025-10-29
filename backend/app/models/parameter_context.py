"""Parameter context models for NiFi parameter management"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class ParameterEntity(BaseModel):
    """Model for a single parameter in a parameter context"""

    name: str
    description: Optional[str] = None
    sensitive: bool = False
    value: Optional[str] = None
    provided: bool = False
    referenced_attributes: Optional[List[str]] = None
    parameter_context_id: Optional[str] = None


class ParameterContext(BaseModel):
    """Model for a NiFi parameter context"""

    id: str
    name: str
    description: Optional[str] = None
    parameters: List[ParameterEntity] = []
    bound_process_groups: Optional[List[Dict[str, Any]]] = None
    inherited_parameter_contexts: Optional[List[str]] = None
    component_revision: Optional[Dict[str, Any]] = None
    permissions: Optional[Dict[str, Any]] = None


class ParameterContextListResponse(BaseModel):
    """Response model for listing parameter contexts"""

    status: str
    parameter_contexts: List[ParameterContext]
    count: int
    message: Optional[str] = None


class ParameterInput(BaseModel):
    """Input model for parameter creation/update"""

    name: str
    description: Optional[str] = None
    sensitive: bool = False
    value: Optional[str] = None


class ParameterContextCreate(BaseModel):
    """Model for creating a parameter context"""

    name: str
    description: Optional[str] = None
    parameters: List[ParameterInput] = []


class ParameterContextUpdate(BaseModel):
    """Model for updating a parameter context"""

    name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[List[ParameterInput]] = None
