from typing import List

from pydantic import BaseModel

from model.lancamento import CategoriaDespesa, CategoriaReceita


class CategoriasSchema(BaseModel):
    """Define como as categorias disponíveis para cada tipo de lançamento
    são apresentadas.
    """
    despesa: List[str] = [categoria.value for categoria in CategoriaDespesa]
    receita: List[str] = [categoria.value for categoria in CategoriaReceita]


def apresenta_categorias() -> dict:
    """Retorna as categorias de despesa e de receita, na ordem em que são
    definidas no modelo
    """
    return {
        "despesa": [categoria.value for categoria in CategoriaDespesa],
        "receita": [categoria.value for categoria in CategoriaReceita],
    }
