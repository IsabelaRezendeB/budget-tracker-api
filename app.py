from decimal import Decimal

from flask import redirect, request
from flask_cors import CORS
from flask_openapi3 import Info, OpenAPI, Tag
from sqlalchemy import case, extract, func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from auth import gera_token, requer_autenticacao
from logger import logger
from model import (
    Dinheiro, Lancamento, Session, Subitem, TipoLancamento, Usuario,
    ZERO_REAIS,
)
from model.lancamento import CATEGORIAS_POR_TIPO
from schemas import (
    CategoriasSchema, ErrorSchema, LancamentoBuscaSchema,
    LancamentoDelSchema, LancamentoListaSchema, LancamentoSchema,
    LancamentoUpdateSchema, LancamentoViewSchema, ListagemLancamentosSchema,
    LoginSchema, MensagemSchema, PeriodoSchema, ResumoSchema,
    SubitemBuscaSchema, SubitemDelSchema,
    SubitemSchema, TokenViewSchema, UsuarioCadastroSchema,
    apresenta_categorias, apresenta_lancamento, apresenta_lancamentos,
    apresenta_usuario,
)

info = Info(title="Budget Tracker API", version="1.0.0")

# Declara o esquema de autenticação para o Swagger renderizar o botão
# "Authorize": basta colar aqui o token obtido em /login ou /cadastro.
security_schemes = {
    "jwt": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
}
app = OpenAPI(__name__, info=info, security_schemes=security_schemes)
CORS(app)

# Lista de segurança aplicada a toda rota que exige autenticação
JWT_SECURITY = [{"jwt": []}]

LANCAMENTO_NAO_ENCONTRADO = "Lançamento não encontrado na base :/"


@app.teardown_appcontext
def encerra_sessao_do_banco(exception=None):
    """Devolve a sessão do banco ao pool ao fim de cada requisição

    Executado tanto em requisições bem-sucedidas quanto com erro.
    """
    Session.remove()


# Definindo tags utilizadas para agrupar as rotas na documentação Swagger
home_tag = Tag(
    name="Documentação",
    description="Seleção de documentação: Swagger, Redoc ou RapiDoc")
usuario_tag = Tag(
    name="Usuário", description="Cadastro, login e logout de usuários")
lancamento_tag = Tag(
    name="Lançamento",
    description="Cadastro, listagem, busca, atualização e remoção de "
                "lançamentos (despesas e receitas)")
subitem_tag = Tag(
    name="Subitem",
    description="Adição e remoção de subitens de um lançamento")
categoria_tag = Tag(
    name="Categoria",
    description="Categorias disponíveis para despesas e receitas")
resumo_tag = Tag(
    name="Resumo",
    description="Totais compartilhados entre despesas e receitas")


# ---------------------------------------------------------------------------
# Funções auxiliares compartilhadas pelas rotas
# ---------------------------------------------------------------------------

def _erro(mensagem: str, status: int, contexto: str):
    """Registra o erro no log e monta a resposta de erro padronizada"""
    logger.warning(f"{contexto}, {mensagem}")
    return {"message": mensagem}, status


def _grava(session, mensagem_erro: str, contexto: str):
    """Confirma as alterações pendentes na sessão do banco.

    Em caso de falha, desfaz a transação (rollback) para a sessão não
    ficar em estado inconsistente e retorna a resposta de erro; se tudo
    der certo, retorna None.
    """
    try:
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        return _erro(mensagem_erro, 400, contexto)
    return None


def _busca_lancamento_do_usuario(session, lancamento_id: int):
    """Busca um lançamento do usuário autenticado pelo id

    Retorna None se ele não existir ou for de outro usuário.
    """
    return session.query(Lancamento).filter(
        Lancamento.id == lancamento_id,
        Lancamento.usuario_id == request.usuario.id,
    ).first()


def _erro_de_categoria(tipo: TipoLancamento, categoria: str, contexto: str):
    """Confere se a categoria é válida para o tipo do lançamento

    Retorna a resposta de erro (400) se não for; se for, retorna None.
    """
    categorias_validas = CATEGORIAS_POR_TIPO[tipo]
    if categoria in categorias_validas:
        return None
    opcoes = ", ".join(sorted(categorias_validas))
    return _erro(f"Categoria inválida para {tipo.value}. "
                 f"Opções válidas: {opcoes}", 400, contexto)


def _filtra_periodo(consulta, periodo: PeriodoSchema):
    """Restringe a consulta de lançamentos ao período informado

    As duas datas são inclusivas.
    """
    if periodo.data_inicio:
        consulta = consulta.filter(Lancamento.data >= periodo.data_inicio)
    if periodo.data_fim:
        consulta = consulta.filter(Lancamento.data <= periodo.data_fim)
    return consulta


def _em_centavos(expressao):
    """Arredonda no próprio SQL um cálculo monetário para 2 casas decimais.

    Toda soma ou média de valores passa por aqui: o SQLite calcula NUMERIC
    em ponto flutuante (0.1 + 0.2 vira 0.30000000000000004), e arredondar
    para centavos elimina esse resíduo.
    """
    return func.round(expressao, 2, type_=Dinheiro)


@app.get('/', tags=[home_tag])
def home():
    """Redireciona para a documentação

    Leva a /openapi, tela que permite escolher entre Swagger, Redoc ou
    RapiDoc.
    """
    return redirect('/openapi')


# ---------------------------------------------------------------------------
# Cadastro, login e logout de usuários
#
# A autenticação é stateless (JWT): o servidor não guarda nenhuma sessão.
# O token retornado no cadastro/login carrega tudo o que é necessário para
# validar as próximas requisições e deve ser enviado no header
# `Authorization: Bearer <token>`. Por isso o "logout" não invalida nada no
# servidor — ele apenas confirma a operação; quem efetivamente encerra o
# acesso é o front-end, ao descartar o token guardado.
# ---------------------------------------------------------------------------

@app.post('/cadastro', tags=[usuario_tag],
          responses={"200": TokenViewSchema, "409": ErrorSchema,
                     "400": ErrorSchema})
def cadastrar_usuario(form: UsuarioCadastroSchema):
    """Cria uma nova conta de usuário

    Já autentica o usuário automaticamente, retornando um token de acesso.
    """
    usuario = Usuario(nome=form.nome, email=form.email, senha=form.senha)
    contexto = f"Erro ao cadastrar usuário '{form.email}'"
    session = Session()
    try:
        session.add(usuario)
        session.commit()
    except IntegrityError:
        session.rollback()
        return _erro("Já existe uma conta cadastrada com esse e-mail :/",
                     409, contexto)
    except SQLAlchemyError:
        session.rollback()
        return _erro("Não foi possível criar a conta :/", 400, contexto)

    logger.debug(f"Conta criada para o e-mail '{usuario.email}'")
    return {"token": gera_token(usuario.id),
            "usuario": apresenta_usuario(usuario)}, 200


@app.post('/login', tags=[usuario_tag],
          responses={"200": TokenViewSchema, "401": ErrorSchema})
def login(form: LoginSchema):
    """Autentica um usuário já cadastrado a partir de e-mail e senha

    Retorna um token de acesso a ser enviado no header
    `Authorization: Bearer <token>` das próximas requisições.
    """
    session = Session()
    usuario = session.query(Usuario).filter(
        Usuario.email == form.email).first()

    if not usuario or not usuario.verifica_senha(form.senha):
        return _erro("E-mail ou senha inválidos", 401,
                     f"Tentativa de login inválida para '{form.email}'")

    logger.debug(f"Login realizado para o e-mail '{usuario.email}'")
    return {"token": gera_token(usuario.id),
            "usuario": apresenta_usuario(usuario)}, 200


@app.post('/logout', tags=[usuario_tag],
          responses={"200": MensagemSchema, "401": ErrorSchema},
          security=JWT_SECURITY)
@requer_autenticacao
def logout():
    """Encerra o acesso do usuário autenticado

    Como a autenticação é stateless, o token em si não é invalidado no
    servidor: é responsabilidade do front-end descartá-lo após esta chamada.
    """
    logger.debug(f"Logout realizado para o e-mail '{request.usuario.email}'")
    return {"message": "Logout realizado com sucesso"}, 200


# ---------------------------------------------------------------------------
# Categorias disponíveis
# ---------------------------------------------------------------------------

@app.get('/categorias', tags=[categoria_tag],
         responses={"200": CategoriasSchema})
def get_categorias():
    """Lista as categorias disponíveis para despesas e para receitas

    É a fonte única dessas opções: o front-end monta o seletor de categoria
    a partir desta rota, em vez de manter uma cópia própria da lista.
    """
    return apresenta_categorias(), 200


# ---------------------------------------------------------------------------
# Cadastro e listagem de lançamentos (despesas e receitas)
#
# Despesa e receita são o mesmo recurso — um lançamento — diferenciados
# pelo campo `tipo`. Por isso todas as rotas abaixo servem aos dois tipos.
# ---------------------------------------------------------------------------

@app.post('/lancamento', tags=[lancamento_tag],
          responses={"200": LancamentoViewSchema, "401": ErrorSchema,
                     "400": ErrorSchema},
          security=JWT_SECURITY)
@requer_autenticacao
def add_lancamento(form: LancamentoSchema):
    """Cadastra um lançamento (despesa ou receita) do usuário autenticado

    O campo `tipo` indica se é uma despesa ou uma receita, e a categoria
    precisa ser compatível com ele (ver GET /categorias). Retorna a
    representação do lançamento cadastrado, com seus subitens.
    """
    contexto = f"Erro ao adicionar {form.tipo.value} '{form.nome}'"
    erro = _erro_de_categoria(form.tipo, form.categoria, contexto)
    if erro:
        return erro

    lancamento = Lancamento(
        tipo=form.tipo,
        nome=form.nome,
        valor=form.valor,
        data=form.data,
        categoria=form.categoria,
        usuario_id=request.usuario.id,
    )
    session = Session()
    session.add(lancamento)
    erro = _grava(session, f"Não foi possível salvar {form.tipo.value} :/",
                  contexto)
    if erro:
        return erro

    logger.debug(f"Adicionado {form.tipo.value} de nome: '{lancamento.nome}'")
    return apresenta_lancamento(lancamento), 200


@app.get('/lancamentos', tags=[lancamento_tag],
         responses={"200": ListagemLancamentosSchema, "401": ErrorSchema},
         security=JWT_SECURITY)
@requer_autenticacao
def get_lancamentos(query: LancamentoListaSchema):
    """Lista os lançamentos do usuário autenticado

    Podem ser filtrados por `tipo` (despesa ou receita) e por período,
    através de `data_inicio` e/ou `data_fim` (datas inclusivas). Retorna a
    listagem da data mais recente para a mais antiga, cada lançamento com
    seus subitens.
    """
    session = Session()
    consulta = session.query(Lancamento).filter(
        Lancamento.usuario_id == request.usuario.id)
    if query.tipo:
        consulta = consulta.filter(Lancamento.tipo == query.tipo)
    consulta = _filtra_periodo(consulta, query)

    # no mesmo dia, o lançamento cadastrado por último aparece primeiro
    lancamentos = consulta.order_by(Lancamento.data.desc(),
                                    Lancamento.id.desc()).all()
    logger.debug(f"Coletados {len(lancamentos)} lançamentos")
    return apresenta_lancamentos(lancamentos), 200


# ---------------------------------------------------------------------------
# Consulta, atualização e remoção de um lançamento específico
# ---------------------------------------------------------------------------

@app.get('/lancamento', tags=[lancamento_tag],
         responses={"200": LancamentoViewSchema, "401": ErrorSchema,
                    "404": ErrorSchema},
         security=JWT_SECURITY)
@requer_autenticacao
def get_lancamento(query: LancamentoBuscaSchema):
    """Busca um lançamento do usuário autenticado pelo id

    O lançamento pode ser uma despesa ou uma receita. Retorna a sua
    representação e a de seus subitens (incluindo o subitem "Outros",
    calculado automaticamente).
    """
    session = Session()
    lancamento = _busca_lancamento_do_usuario(session, query.id)
    if not lancamento:
        return _erro(LANCAMENTO_NAO_ENCONTRADO, 404,
                     f"Erro ao buscar lançamento #{query.id}")

    logger.debug(f"Lançamento encontrado: #{lancamento.id}")
    return apresenta_lancamento(lancamento), 200


@app.put('/lancamento', tags=[lancamento_tag],
         responses={"200": LancamentoViewSchema, "401": ErrorSchema,
                    "404": ErrorSchema, "400": ErrorSchema},
         security=JWT_SECURITY)
@requer_autenticacao
def update_lancamento(form: LancamentoUpdateSchema):
    """Atualiza um lançamento do usuário autenticado

    Altera nome, valor, data e/ou categoria; campos não informados
    permanecem com o valor atual. Retorna a representação atualizada do
    lançamento.
    """
    contexto = f"Erro ao atualizar lançamento #{form.id}"
    session = Session()
    lancamento = _busca_lancamento_do_usuario(session, form.id)
    if not lancamento:
        return _erro(LANCAMENTO_NAO_ENCONTRADO, 404, contexto)

    if form.nome is not None:
        lancamento.nome = form.nome
    if form.valor is not None:
        # o valor não pode cair abaixo do que os subitens já cadastrados
        # somam
        soma_subitens = lancamento.total_subitens()
        if form.valor < soma_subitens:
            return _erro(
                f"Não é possível reduzir o valor para {form.valor:.2f}: os "
                f"subitens já cadastrados somam {soma_subitens:.2f}. Ajuste "
                f"ou remova subitens antes de diminuir o valor.",
                400, contexto)
        lancamento.valor = form.valor
    if form.data is not None:
        lancamento.data = form.data
    if form.categoria is not None:
        erro = _erro_de_categoria(lancamento.tipo, form.categoria, contexto)
        if erro:
            return erro
        lancamento.categoria = form.categoria

    erro = _grava(session, "Não foi possível atualizar o lançamento :/",
                  contexto)
    if erro:
        return erro

    logger.debug(f"Atualizado lançamento #{form.id}")
    return apresenta_lancamento(lancamento), 200


@app.delete('/lancamento', tags=[lancamento_tag],
            responses={"200": LancamentoDelSchema, "401": ErrorSchema,
                       "404": ErrorSchema, "400": ErrorSchema},
            security=JWT_SECURITY)
@requer_autenticacao
def del_lancamento(query: LancamentoBuscaSchema):
    """Remove um lançamento do usuário autenticado pelo id

    Os subitens do lançamento são removidos junto. Retorna uma mensagem
    de confirmação da remoção.
    """
    contexto = f"Erro ao deletar lançamento #{query.id}"
    session = Session()
    lancamento = _busca_lancamento_do_usuario(session, query.id)
    if not lancamento:
        return _erro(LANCAMENTO_NAO_ENCONTRADO, 404, contexto)

    session.delete(lancamento)
    erro = _grava(session, "Não foi possível remover o lançamento :/",
                  contexto)
    if erro:
        return erro

    logger.debug(f"Deletado lançamento #{query.id}")
    return {"message": "Lançamento removido", "id": query.id}, 200


# ---------------------------------------------------------------------------
# Subitens de um lançamento
# ---------------------------------------------------------------------------

@app.post('/subitem', tags=[subitem_tag],
          responses={"200": LancamentoViewSchema, "401": ErrorSchema,
                     "404": ErrorSchema, "400": ErrorSchema},
          security=JWT_SECURITY)
@requer_autenticacao
def add_subitem(form: SubitemSchema):
    """Adiciona um subitem a um lançamento do usuário autenticado

    A soma dos subitens não pode ultrapassar o valor total do lançamento —
    a parte ainda não distribuída é apresentada automaticamente como um
    subitem "Outros". Retorna a representação do lançamento e de seus
    subitens.
    """
    contexto = f"Erro ao adicionar subitem ao lançamento #{form.lancamento_id}"
    session = Session()
    lancamento = _busca_lancamento_do_usuario(session, form.lancamento_id)
    if not lancamento:
        return _erro(LANCAMENTO_NAO_ENCONTRADO, 404, contexto)

    soma_apos_adicionar = lancamento.total_subitens() + form.valor
    if soma_apos_adicionar > lancamento.valor:
        return _erro(
            f"Não é possível adicionar este subitem: a soma dos subitens "
            f"({soma_apos_adicionar:.2f}) ultrapassaria o valor total do "
            f"lançamento ({lancamento.valor:.2f}).",
            400, contexto)

    subitem = Subitem(nome=form.nome, valor=form.valor)
    lancamento.adiciona_subitem(subitem)
    erro = _grava(session, "Não foi possível adicionar o subitem :/",
                  contexto)
    if erro:
        return erro

    logger.debug(f"Adicionado subitem '{subitem.nome}' ao lançamento "
                 f"#{form.lancamento_id}")
    return apresenta_lancamento(lancamento), 200


@app.delete('/subitem', tags=[subitem_tag],
            responses={"200": SubitemDelSchema, "401": ErrorSchema,
                       "404": ErrorSchema, "400": ErrorSchema},
            security=JWT_SECURITY)
@requer_autenticacao
def del_subitem(query: SubitemBuscaSchema):
    """Remove um subitem do usuário autenticado pelo id

    O valor liberado volta automaticamente a fazer parte do subitem
    "Outros" do lançamento ao qual pertencia. Retorna uma mensagem de
    confirmação da remoção.
    """
    contexto = f"Erro ao deletar subitem #{query.id}"
    session = Session()
    subitem = session.query(Subitem).join(
        Lancamento, Subitem.lancamento == Lancamento.id
    ).filter(
        Subitem.id == query.id,
        Lancamento.usuario_id == request.usuario.id,
    ).first()
    if not subitem:
        return _erro("Subitem não encontrado na base :/", 404, contexto)

    session.delete(subitem)
    erro = _grava(session, "Não foi possível remover o subitem :/",
                  contexto)
    if erro:
        return erro

    logger.debug(f"Deletado subitem #{query.id}")
    return {"message": "Subitem removido", "id": query.id}, 200


# ---------------------------------------------------------------------------
# Resumo financeiro (total compartilhado entre despesas e receitas)
# ---------------------------------------------------------------------------

@app.get('/resumo', tags=[resumo_tag],
         responses={"200": ResumoSchema, "401": ErrorSchema},
         security=JWT_SECURITY)
@requer_autenticacao
def get_resumo(query: PeriodoSchema):
    """Calcula as métricas financeiras do usuário autenticado

    Podem ser restritas a um período através de `data_inicio` e/ou
    `data_fim` (datas inclusivas). Retorna o total de despesas, o total de
    receitas, o saldo entre elas (receitas - despesas), a média de saldo
    por mês (considerando os meses em que houve algum lançamento) e a
    categoria de despesa com maior valor acumulado.
    """
    session = Session()

    def consulta_no_periodo(*colunas):
        """Consulta das colunas informadas, restrita aos lançamentos do
        usuário autenticado dentro do período pedido
        """
        consulta = session.query(*colunas).filter(
            Lancamento.usuario_id == request.usuario.id)
        return _filtra_periodo(consulta, query)

    # Totais por tipo em uma única consulta:
    # SELECT tipo, ROUND(SUM(valor), 2) ... GROUP BY tipo
    totais_por_tipo = dict(
        consulta_no_periodo(Lancamento.tipo,
                            _em_centavos(func.sum(Lancamento.valor)))
        .group_by(Lancamento.tipo)
        .all())
    total_despesas = totais_por_tipo.get(TipoLancamento.despesa, ZERO_REAIS)
    total_receitas = totais_por_tipo.get(TipoLancamento.receita, ZERO_REAIS)

    # Saldo de cada mês em que houve lançamento (receitas somam, despesas
    # subtraem) numa subconsulta agrupada por ano e mês; a consulta externa
    # tira a média (AVG) desses saldos mensais.
    #
    # A média é tirada sobre os saldos em centavos inteiros: em reais, uma
    # média de 0,015 viraria 0,01499... em ponto flutuante e seria
    # arredondada para baixo; em centavos ela é exatamente 1,5.
    valor_com_sinal = case(
        (Lancamento.tipo == TipoLancamento.receita, Lancamento.valor),
        else_=-Lancamento.valor)
    saldos_mensais = (
        consulta_no_periodo(
            _em_centavos(func.sum(valor_com_sinal)).label("saldo"))
        .group_by(extract("year", Lancamento.data),
                  extract("month", Lancamento.data))
        .subquery())
    saldo_em_centavos = func.round(saldos_mensais.c.saldo * 100)
    media_em_centavos = session.query(
        func.round(func.avg(saldo_em_centavos))).scalar()
    media_saldo_mensal = Decimal(int(media_em_centavos or 0)) / 100

    # Categoria de despesa com maior soma: agrupa por categoria, ordena pela
    # soma decrescente (empate: ordem alfabética) e fica com a primeira.
    soma_da_categoria = _em_centavos(func.sum(Lancamento.valor))
    categoria_mais_gasto = (
        consulta_no_periodo(Lancamento.categoria)
        .filter(Lancamento.tipo == TipoLancamento.despesa)
        .group_by(Lancamento.categoria)
        .order_by(soma_da_categoria.desc(), Lancamento.categoria)
        .limit(1)
        .scalar())

    logger.debug("Resumo financeiro calculado")
    return {
        "total_despesas": float(total_despesas),
        "total_receitas": float(total_receitas),
        "saldo": float(total_receitas - total_despesas),
        "media_saldo_mensal": float(media_saldo_mensal),
        "categoria_mais_gasto": categoria_mais_gasto,
    }, 200
