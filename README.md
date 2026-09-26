# Budget Tracker API

API REST do Budget Tracker — projeto do MVP da disciplina **Desenvolvimento
Full Stack Básico** (PUC-Rio). Cada usuário cria sua conta e gerencia suas
próprias despesas e receitas, com subitens e totais.

## Pré-requisitos

- [Python 3.10+](https://www.python.org/downloads/) instalado

## Passo a passo para rodar

1. Baixe/clone este repositório e, pelo terminal, entre na pasta dele.

2. Crie um ambiente virtual:

   ```
   python -m venv env
   ```

3. Ative o ambiente virtual:

   - Linux/Mac: `source env/bin/activate`
   - Windows: `env\Scripts\activate`

4. Instale as dependências:

   ```
   pip install -r requirements.txt
   ```

5. Rode a API:

   ```
   flask run --host 0.0.0.0 --port 5000
   ```

6. Pronto! A API está disponível em:

   - **Documentação (Swagger)**: http://localhost:5000/openapi
   - **Rotas**: http://localhost:5000

O banco SQLite é criado automaticamente na primeira execução, em
`database/db.sqlite3`.

## Testando pelo Swagger

Todas as rotas (exceto cadastro, login e categorias) exigem autenticação:

1. Crie uma conta em `POST /cadastro` ou faça login em `POST /login` — a
   resposta traz um `token`.
2. Clique no botão **Authorize** (no topo da página do Swagger) e cole
   apenas o token, sem o prefixo `Bearer` — o próprio Swagger o acrescenta.
3. Agora as demais rotas podem ser testadas normalmente por ali.

> Observação: a chave usada para assinar o token (em `auth.py`) é fixa no
> código por se tratar de um projeto didático. Em um ambiente real, ela
> deveria vir de uma variável de ambiente.
