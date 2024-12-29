from typing import Any, Dict, List
from pydantic import BaseModel

class BaseAgent(BaseModel):
    """基礎代理類別"""
    name: str
    description: str
    
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """執行代理邏輯"""
        raise NotImplementedError 