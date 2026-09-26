from typing import Optional

from pydantic import BaseModel


class ResumoSchema(BaseModel):
    """Define a estrutura do resumo financeiro, com os totais e métricas
    compartilhados entre a lista de despesas e a lista de receitas.
    """
    total_despesas: float = 0.0
    total_receitas: float = 0.0
    saldo: float = 0.0
    media_saldo_mensal: float = 0.0
    categoria_mais_gasto: Optional[str] = None
