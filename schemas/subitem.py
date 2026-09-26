from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from schemas.tipos import ValorMonetario


class SubitemSchema(BaseModel):
    """Define como um novo subitem deve ser representado ao ser inserido
    em um lançamento já cadastrado.
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    lancamento_id: int = 1
    nome: str = Field("Morangos", min_length=1)
    valor: ValorMonetario = Decimal("20.00")


class SubitemBuscaSchema(BaseModel):
    """Define a estrutura usada para localizar/remover um subitem pelo
    id
    """
    id: int = 1


class SubitemViewSchema(BaseModel):
    """Define como um subitem é apresentado dentro de um lançamento.

    Quando `automatico` é `true`, o subitem não existe na base — ele
    representa a parcela do valor do lançamento ainda não distribuída
    entre os subitens cadastrados manualmente (o subitem "Outros").
    """
    id: Optional[int] = None
    nome: str
    valor: float
    automatico: bool = False


class SubitemDelSchema(BaseModel):
    """Define a estrutura do dado retornado após a remoção de um
    subitem
    """
    message: str
    id: int
