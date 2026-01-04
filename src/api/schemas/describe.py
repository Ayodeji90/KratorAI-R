from pydantic import BaseModel

class DescribeResponse(BaseModel):
    """Enhanced response from multi-stage pipeline."""
    description: str
    category: str
    style: list[str] = []
    editable_elements: list[str] = []
    design_quality: str = "unknown"
    target_audience: str = "unknown"
    vision_data: dict = {}  # Raw vision extraction data
    source: str = "vision+o3-mini"
