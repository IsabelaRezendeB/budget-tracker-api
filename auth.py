import datetime as dt
from functools import wraps

import jwt
from flask import request

from model import Session, Usuario

# Em produção, este valor deve vir de uma variável de ambiente e nunca ser
# versionado no código-fonte. Como este é um projeto didático (MVP), o
# segredo fica fixo aqui por simplicidade.
SECRET_KEY = "budget-tracker-mvp-chave-secreta-de-desenvolvimento"
ALGORITMO = "HS256"
EXPIRACAO_HORAS = 12


def gera_token(usuario_id: int) -> str:
    """Gera um token JWT contendo o id do usuário e uma data de expiração.

    A autenticação aqui é stateless: nenhuma sessão fica guardada no
    servidor — o próprio token, assinado com `SECRET_KEY`, carrega tudo o
    que é necessário para validar as próximas requisições do usuário.
    """
    payload = {
        # o claim "sub" precisa ser string — é uma exigência do próprio PyJWT
        "sub": str(usuario_id),
        "exp": (dt.datetime.now(dt.timezone.utc)
                + dt.timedelta(hours=EXPIRACAO_HORAS)),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITMO)


def _usuario_autenticado():
    """Lê o header Authorization, valida o token e retorna o Usuario
    correspondente (ou None caso ausente, inválido ou expirado).
    """
    cabecalho = request.headers.get("Authorization", "")
    if not cabecalho.startswith("Bearer "):
        return None

    token = cabecalho[len("Bearer "):]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITMO])
    except jwt.PyJWTError:
        return None

    session = Session()
    usuario_id = int(payload["sub"])
    return session.query(Usuario).filter(Usuario.id == usuario_id).first()


def requer_autenticacao(rota):
    """Decorator que exige um token JWT válido no header
    `Authorization: Bearer <token>`.

    Disponibiliza o usuário autenticado em `request.usuario` para a rota
    decorada utilizar.
    """
    @wraps(rota)
    def rota_protegida(*args, **kwargs):
        usuario = _usuario_autenticado()
        if not usuario:
            mensagem = "Token de autenticação ausente, inválido ou expirado"
            return {"message": mensagem}, 401
        request.usuario = usuario
        return rota(*args, **kwargs)
    return rota_protegida
