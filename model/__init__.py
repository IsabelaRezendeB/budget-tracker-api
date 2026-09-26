import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy_utils import create_database, database_exists

# Importando os elementos definidos no modelo, na ordem correta de
# dependência
from model.base import Base, Dinheiro, ZERO_REAIS
from model.usuario import Usuario
from model.subitem import Subitem
from model.lancamento import Lancamento, TipoLancamento

# Nomes que o pacote `model` disponibiliza para o restante da aplicação
__all__ = [
    "Base", "Dinheiro", "ZERO_REAIS", "Usuario", "Subitem", "Lancamento",
    "TipoLancamento", "Session",
]

# O banco SQLite fica em um arquivo local, dentro da pasta database/
PASTA_BANCO = "database"
os.makedirs(PASTA_BANCO, exist_ok=True)
engine = create_engine(f"sqlite:///{PASTA_BANCO}/db.sqlite3", echo=False)

# Instancia um criador de sessão com o banco. `scoped_session` reaproveita a
# mesma sessão dentro de uma mesma requisição/thread e, junto ao
# `teardown_appcontext` registrado em app.py, garante que a conexão volte
# para o pool ao final de cada requisição — sem isso, cada chamada a
# `Session()` abre uma conexão nova que nunca é liberada, e o pool se esgota
# depois de tempo suficiente de uso (erro 500 por "QueuePool timeout").
Session = scoped_session(sessionmaker(bind=engine))

# Na primeira execução, cria o arquivo do banco e as tabelas
if not database_exists(engine.url):
    create_database(engine.url)
Base.metadata.create_all(engine)
