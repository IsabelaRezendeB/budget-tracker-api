from pydantic import BaseModel


class ErrorSchema(BaseModel):
    """Representa uma mensagem de erro retornada pela API"""
    message: str
