from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

# Formato mínimo de e-mail: algo@dominio.ext, sem espaços
PADRAO_EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
TAMANHO_MINIMO_SENHA = 6


class UsuarioCadastroSchema(BaseModel):
    """Define os dados necessários para criar uma nova conta de usuário"""
    nome: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1),
    ] = "Maria Silva"
    email: Annotated[
        str, StringConstraints(strip_whitespace=True, pattern=PADRAO_EMAIL),
    ] = "maria@email.com"
    # a senha não passa por strip: espaços fazem parte dela
    senha: str = Field("minhasenha123", min_length=TAMANHO_MINIMO_SENHA)


class LoginSchema(BaseModel):
    """Define os dados necessários para autenticar um usuário já cadastrado"""
    email: str = "maria@email.com"
    senha: str = "minhasenha123"


class UsuarioViewSchema(BaseModel):
    """Define como os dados públicos de um usuário são apresentados.

    Nunca inclui a senha ou o hash da senha.
    """
    id: int = 1
    nome: str = "Maria Silva"
    email: str = "maria@email.com"


class TokenViewSchema(BaseModel):
    """Define a resposta do cadastro e do login: o token de autenticação
    (a ser enviado no header `Authorization: Bearer <token>` das próximas
    requisições) e os dados públicos do usuário autenticado.
    """
    token: str
    usuario: UsuarioViewSchema


class MensagemSchema(BaseModel):
    """Define uma resposta simples de confirmação"""
    message: str


def apresenta_usuario(usuario) -> dict:
    """Retorna a representação pública de um usuário (sem dados sensíveis)"""
    return {"id": usuario.id, "nome": usuario.nome, "email": usuario.email}
