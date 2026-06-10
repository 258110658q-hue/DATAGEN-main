from pydantic import BaseModel, Field
from typing import Dict

class ArtifactSchema(BaseModel):
    """工作代理生成工件的标准输出模式。"""
    summary: str = Field(description="对所执行操作及关键发现的简洁总结。")
    artifacts: Dict[str, str] = Field(
        default_factory=dict,
        description="将文件路径映射到其描述的字典（例如，{'output/chart.png': '销售趋势图'}）。"
    )
