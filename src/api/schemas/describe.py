from pydantic import BaseModel

class DescribeResponse(BaseModel):
    description: str
