from decimal import Decimal

from sqlalchemy import Column, ForeignKey, Integer, String

from model import Base, Dinheiro


class Subitem(Base):
    """Um subitem representa uma parte do valor de um Lancamento.

    Exemplo: um lançamento "Compras" de R$ 30 pode ter os subitens
    "Morangos" (R$ 20) e "Macarrão" (R$ 10). O subitem não tem data própria:
    ele se refere sempre ao dia do lançamento ao qual pertence.
    """
    __tablename__ = 'subitem'

    id = Column("pk_subitem", Integer, primary_key=True)
    nome = Column(String(140), nullable=False)
    valor = Column(Dinheiro, nullable=False)

    # Chave estrangeira que relaciona o subitem ao lançamento ao qual pertence
    lancamento = Column(Integer, ForeignKey("lancamento.pk_lancamento"),
                        nullable=False)

    def __init__(self, nome: str, valor: Decimal):
        """
        Cria um Subitem

        Arguments:
            nome: nome do subitem.
            valor: valor correspondente a esse subitem.
        """
        self.nome = nome
        self.valor = valor
