from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class SubTask(BaseModel):
    id: str
    description: str
    dependencies: List[str] = Field(default_factory=list)

class TaskPlan(BaseModel):
    intent: str
    subtasks: List[SubTask]
    
class ExecutionTrace(BaseModel):
    task_id: str
    tool_name: str
    inputs: Dict[str, Any]
    status: str # 'success' or 'error'
    result: Optional[str] = None
    error_message: Optional[str] = None
    latency_ms: Optional[int] = None

class CapabilitySchema(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any] # JSON schema of parameters
    code: str # The python code string generated
    constraints: List[str] = Field(default_factory=list)
