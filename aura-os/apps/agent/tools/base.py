from pydantic import BaseModel
from typing import Callable, Any, Dict, List, Optional
import inspect

class ToolInfo(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]
    risk_level: str               # SAFE, MODERATE, DANGEROUS, CRITICAL
    required_permission: str      # read-only, filesystem-write, execution, destructive
    # The verify method takes the task_id, tool arguments, and execution output, and confirms success
    verify_method: Optional[Callable[..., Any]] = None

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, tuple[Callable[..., Any], ToolInfo]] = {}

    def register(
        self,
        name: str,
        description: str,
        risk_level: str,
        required_permission: str,
        verify_method: Optional[Callable[..., Any]] = None
    ):
        """Decorator to register a tool function."""
        def decorator(func: Callable[..., Any]):
            # Auto-generate parameters schema from function signature using reflection if not provided
            sig = inspect.signature(func)
            parameters = {
                "type": "object",
                "properties": {},
                "required": []
            }
            
            for param_name, param in sig.parameters.items():
                if param_name == "self" or param_name == "task_id":
                    continue  # Skip framework arguments
                
                param_type = "string"
                if param.annotation == int:
                    param_type = "integer"
                elif param.annotation == bool:
                    param_type = "boolean"
                elif param.annotation == float:
                    param_type = "number"
                elif param.annotation == dict:
                    param_type = "object"
                elif param.annotation == list:
                    param_type = "array"

                parameters["properties"][param_name] = {
                    "type": param_type,
                    "description": f"Argument {param_name}"
                }
                
                if param.default == inspect.Parameter.empty:
                    parameters["required"].append(param_name)

            info = ToolInfo(
                name=name,
                description=description,
                parameters=parameters,
                risk_level=risk_level,
                required_permission=required_permission,
                verify_method=verify_method
            )
            self._tools[name] = (func, info)
            return func
        return decorator

    def get_tool(self, name: str) -> Optional[tuple[Callable[..., Any], ToolInfo]]:
        return self._tools.get(name)

    def list_tools(self) -> List[ToolInfo]:
        return [info for _, info in self._tools.values()]

    def list_gemini_schemas(self) -> List[Dict[str, Any]]:
        """Converts registered tools into Gemini tool schemas."""
        schemas = []
        for name, (func, info) in self._tools.items():
            schemas.append({
                "function_declarations": [{
                    "name": info.name,
                    "description": info.description,
                    "parameters": info.parameters
                }]
            })
        return schemas

# Global Tool Registry instance
registry = ToolRegistry()
