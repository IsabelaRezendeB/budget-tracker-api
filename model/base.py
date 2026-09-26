from decimal import Decimal

from sqlalchemy import Numeric
from sqlalchemy.orm import declarative_base

# Classe Base utilizada para o mapeamento das tabelas do banco de dados
Base = declarative_base()

# Tipo das colunas de valores monetários: NUMERIC com 2 casas decimais
# (centavos). O SQLAlchemy devolve esses valores como Decimal, então somas e
# comparações no Python são exatas — com float, 0.1 + 0.2 daria
# 0.30000000000000004 e a soma dos subitens poderia "ultrapassar" o total.
Dinheiro = Numeric(precision=12, scale=2)

ZERO_REAIS = Decimal("0.00")
