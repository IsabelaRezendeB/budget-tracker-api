from datetime import date
from typing import Optional

from pydantic import BaseModel, model_validator


class PeriodoSchema(BaseModel):
    """Define o filtro opcional de período usado nas listagens de despesas
    e receitas e no resumo financeiro.

    As duas datas são inclusivas; qualquer uma delas pode ser omitida.
    """
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None

    @model_validator(mode="after")
    def _inicio_antes_do_fim(self):
        if (self.data_inicio and self.data_fim
                and self.data_inicio > self.data_fim):
            raise ValueError(
                "A data inicial não pode ser posterior à data final.")
        return self
