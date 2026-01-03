from pydantic import BaseModel

class DescribeResponse(BaseModel):
    description: str
    tags: list[str] = []
    extracted_text: str = ""
