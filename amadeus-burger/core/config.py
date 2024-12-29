from pydantic import BaseModel, Field
from typing import Optional

class AmadeusConfig(BaseModel):
    """系統設定"""
    openai_api_key: Optional[str] = Field(None, description="OpenAI API 金鑰")
    model_name: str = Field("gpt-4-turbo-preview", description="預設使用的 LLM 模型")
    temperature: float = Field(0.7, description="生成溫度") 