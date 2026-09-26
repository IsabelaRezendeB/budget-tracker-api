from datetime import datetime
from decimal import Decimal
from typing import Union

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from model import Base, Dinheiro


class Subitem(Base):
    """Um subitem representa uma parte do valor de um Lancamento.

    Exemplo: um lançamento "Compras" de R$ 30 pode ter os subitens
    "Morangos" (R$ 20) e "Macarrão" (R$ 10).
    """
    __tablename__ = 'subitem'

    id = Column("pk_subitem", Integer, primary_key=True)
    nome = Column(String(140), nullable=False)
    valor = Column(Dinheiro, nullable=False)
    data_insercao = Column(DateTime, default=datetime.now)

    # Chave estrangeira que relaciona o subitem ao lançamento ao qual pertence
    lancamento = Column(Integer, ForeignKey("lancamento.pk_lancamento"),
                        nullable=False)

    def __init__(self, nome: str, valor: Decimal,
                 data_insercao: Union[datetime, None] = None):
        """
        Cria um Subitem

        Arguments:
            nome: nome do subitem.
            valor: valor correspondente a esse subitem.
            data_insercao: data de quando o subitem foi inserido na base.
        """
        self.nome = nome
        self.valor = valor
        if data_insercao:
            self.data_insercao = data_insercao
