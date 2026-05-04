from typing import Type

from langchain_core.tools import tool, BaseTool
from pydantic import BaseModel, Field

from model.qwen_llm import llm
# ----------------------
# 步骤1：定义工具的 Schema（给 LLM 看的参数结构）
# ----------------------
class MultiplyInput(BaseModel):
    a: float = Field(description="数字A，例如 2")
    b: float = Field(description="数字B，例如 3")

# ----------------------
# 步骤2：定义工具本身
# ----------------------
class MultiplyTool(BaseTool):
    name: str = "multiply"
    description: str = "两个数字相乘，计算 a × b"
    args_schema: Type[BaseModel] = MultiplyInput  # 关键：function calling 用的 schema

    def _run(self, a: float, b: float):
        return f"计算结果：{a} × {b} = {a * b}"

# ----------------------
# 步骤3：创建工具实例（给 LLM 使用）
# ----------------------
multiply_tool = MultiplyTool()

llm_with_tools = llm.bind_tools([multiply_tool])
resp  = llm_with_tools.invoke("请计算 3.5 乘以 4")
print(resp.tool_calls)
result = multiply_tool.run(resp.tool_calls[0]["args"])
print(result)
