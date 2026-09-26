import enum
from datetime import date
from decimal import Decimal

from sqlalchemy import Column, Date, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from model import Base, Dinheiro, ZERO_REAIS
from model.subitem import Subitem


class TipoLancamento(str, enum.Enum):
    """Um lançamento financeiro é sempre uma despesa ou uma receita."""
    despesa = "despesa"
    receita = "receita"


class CategoriaDespesa(str, enum.Enum):
    """Categorias fixas disponíveis para uma despesa"""
    entretenimento = "Entretenimento"
    comida = "Comida"
    transporte = "Transporte"
    moradia = "Moradia"
    outros = "Outros"


class CategoriaReceita(str, enum.Enum):
    """Categorias fixas disponíveis para uma receita"""
    salario = "Salário"
    bonus = "Bônus"
    presente = "Presente"
    outros = "Outros"


# Usado para validar, no cadastro e na atualização de um lançamento, se a
# categoria informada é compatível com o tipo (despesa/receita) dele.
CATEGORIAS_POR_TIPO = {
    TipoLancamento.despesa: {categoria.value
                             for categoria in CategoriaDespesa},
    TipoLancamento.receita: {categoria.value
                             for categoria in CategoriaReceita},
}


class Lancamento(Base):
    """Uma despesa ou receita cadastrada pelo usuário.

    Um Lancamento pode ter zero ou mais Subitens associados. A parte do
    valor do lançamento que ainda não foi distribuída entre os subitens
    cadastrados é sempre apresentada como um subitem "Outros" calculado
    em tempo de leitura (ver `restante_outros`) — ela nunca é persistida
    na base, pois deve refletir o estado atual dos subitens a qualquer momento.
    """
    __tablename__ = 'lancamento'

    id = Column("pk_lancamento", Integer, primary_key=True)
    tipo = Column(Enum(TipoLancamento), nullable=False)
    nome = Column(String(140), nullable=False)
    valor = Column(Dinheiro, nullable=False)
    # Dia em que a despesa ou receita aconteceu, escolhido pelo usuário (pode
    # ser anterior ao cadastro). Guarda só a data, sem hora.
    data = Column(Date, nullable=False)
    # Um dos valores de CategoriaDespesa/CategoriaReceita, conforme o tipo.
    # A validação de qual conjunto vale é feita nas rotas (em app.py), já
    # que essa coluna serve tanto despesas quanto receitas.
    categoria = Column(String(50), nullable=False, default="Outros")

    # Todo lançamento pertence a um usuário; só o dono pode vê-lo, editá-lo
    # ou removê-lo (essa checagem é feita nas rotas, em app.py).
    usuario_id = Column(Integer, ForeignKey("usuario.pk_usuario"),
                        nullable=False)

    # Um lançamento pode ter vários subitens; ao remover o lançamento,
    # seus subitens são removidos junto (cascade).
    subitens = relationship("Subitem", cascade="all, delete-orphan")

    def __init__(self, tipo: TipoLancamento, nome: str, valor: Decimal,
                 data: date, usuario_id: int, categoria: str = "Outros"):
        """
        Cria uma despesa ou receita

        Arguments:
            tipo: se o lançamento é uma "despesa" ou uma "receita".
            nome: nome do lançamento.
            valor: valor total do lançamento.
            data: data em que a despesa ou receita ocorreu.
            usuario_id: id do usuário dono deste lançamento.
            categoria: categoria do lançamento (ver CategoriaDespesa e
                CategoriaReceita).
        """
        self.tipo = tipo
        self.nome = nome
        self.valor = valor
        self.data = data
        self.usuario_id = usuario_id
        self.categoria = categoria

    def adiciona_subitem(self, subitem: Subitem):
        """Adiciona um novo subitem ao Lancamento"""
        self.subitens.append(subitem)

    def total_subitens(self) -> Decimal:
        """Soma dos valores dos subitens efetivamente cadastrados"""
        return sum((subitem.valor for subitem in self.subitens), ZERO_REAIS)

    def restante_outros(self) -> Decimal:
        """Parcela do valor do lançamento ainda não distribuída em subitens.

        Enquanto o total dos subitens cadastrados for menor que o valor do
        lançamento, a diferença é considerada parte do subitem "Outros".
        """
        restante = self.valor - self.total_subitens()
        return restante if restante > 0 else ZERO_REAIS
