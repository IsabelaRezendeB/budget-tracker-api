from datetime import date, datetime, time
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from model.lancamento import Lancamento, TipoLancamento
from schemas.periodo import PeriodoSchema
from schemas.subitem import SubitemViewSchema
from schemas.tipos import ValorMonetario

DESCRICAO_DATA = "Data do lançamento. Se omitida, assume o dia atual."


def hoje() -> datetime:
    """Data do dia atual (à meia-noite), calculada a cada chamada.

    É o padrão do campo `data` no cadastro: usar `datetime.now()` direto
    como default fixaria a data do momento em que o servidor subiu.
    """
    return datetime.combine(date.today(), time.min)


def _vazia_vira_hoje(valor):
    # um form que deixou a data em branco (ex.: o Swagger) cai no dia atual
    return valor or hoje()


class LancamentoSchema(BaseModel):
    """Define como um novo lançamento (despesa ou receita) deve ser
    representado ao ser cadastrado.

    `categoria` precisa ser uma das opções do tipo escolhido (ver
    GET /categorias); quando omitida, assume "Outros".
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    tipo: TipoLancamento = TipoLancamento.despesa
    nome: str = Field("Compras do mês", min_length=1)
    valor: ValorMonetario = Decimal("30.00")
    data: datetime = Field(default_factory=hoje, description=DESCRICAO_DATA)
    categoria: str = Field(
        "Outros",
        description="Categoria compatível com o tipo (ver GET /categorias).")

    @field_validator("categoria", mode="before")
    @classmethod
    def _vazio_vira_outros(cls, valor):
        # se vier em branco (ex.: um form que não preencheu o campo),
        # cai no padrão "Outros" em vez de falhar a validação
        return valor or "Outros"

    _data_padrao = field_validator("data", mode="before")(_vazia_vira_hoje)


class LancamentoListaSchema(PeriodoSchema):
    """Define os filtros opcionais da listagem de lançamentos: o tipo
    (despesa ou receita) e o período.

    Sem `tipo`, a listagem traz despesas e receitas juntas.
    """
    tipo: Optional[TipoLancamento] = None


class LancamentoBuscaSchema(BaseModel):
    """Define a estrutura usada para localizar, atualizar ou remover um
    lançamento a partir do seu id.
    """
    id: int = 1


class LancamentoUpdateSchema(BaseModel):
    """Define os campos que podem ser atualizados em um lançamento já
    existente. Campos não informados permanecem inalterados.

    `categoria` aceita string livre aqui porque o schema é compartilhado
    entre despesas e receitas — a validação de qual conjunto de categorias
    é válido para aquele lançamento específico é feita na rota, com base no
    tipo do lançamento já cadastrado.
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    id: int = 1
    nome: Optional[str] = Field(None, min_length=1)
    valor: Optional[ValorMonetario] = None
    data: Optional[datetime] = None
    categoria: Optional[str] = None


class LancamentoViewSchema(BaseModel):
    """Define como uma despesa ou receita é apresentada, junto com seus
    subitens (incluindo o subitem "Outros", calculado automaticamente).
    """
    id: int = 1
    tipo: TipoLancamento
    nome: str = "Compras do mês"
    valor: float = 30.0
    data: datetime
    categoria: Optional[str] = None
    quantidade_subitens: int
    subitens: List[SubitemViewSchema]


class ListagemLancamentosSchema(BaseModel):
    """Define como uma listagem de lançamentos é retornada"""
    lancamentos: List[LancamentoViewSchema]


class LancamentoDelSchema(BaseModel):
    """Define a estrutura do dado retornado após a remoção de um
    lançamento
    """
    message: str
    id: int


def apresenta_lancamento(lancamento: Lancamento) -> dict:
    """Retorna a representação de um lançamento e seus subitens, incluindo
    o subitem "Outros" com o valor ainda não distribuído (quando houver).

    Os valores são calculados como Decimal e só convertidos para número
    (float) aqui, na hora de montar o JSON da resposta.

    O subitem "Outros" só é exibido quando já existe ao menos um subitem
    cadastrado manualmente — um lançamento sem nenhum subitem é exibido
    apenas com o seu valor total, sem quebrar em partes.
    """
    subitens = [
        {"id": subitem.id, "nome": subitem.nome,
         "valor": float(subitem.valor), "automatico": False}
        for subitem in lancamento.subitens
    ]

    if subitens:
        restante = lancamento.restante_outros()
        if restante > 0:
            subitens.append({"id": None, "nome": "Outros",
                             "valor": float(restante), "automatico": True})

    return {
        "id": lancamento.id,
        "tipo": lancamento.tipo,
        "nome": lancamento.nome,
        "valor": float(lancamento.valor),
        "data": lancamento.data.isoformat(),
        "categoria": lancamento.categoria,
        "quantidade_subitens": len(subitens),
        "subitens": subitens,
    }


def apresenta_lancamentos(lancamentos: List[Lancamento]) -> dict:
    """Retorna a representação de uma listagem de lançamentos"""
    return {"lancamentos": [apresenta_lancamento(lancamento)
                            for lancamento in lancamentos]}
