from decimal import Decimal
from typing import Annotated

from pydantic import Field

# Valor monetário recebido pela API: positivo, com até 2 casas decimais
# (centavos) e no máximo 12 dígitos — o mesmo formato da coluna Dinheiro.
ValorMonetario = Annotated[
    Decimal, Field(gt=0, max_digits=12, decimal_places=2),
]
