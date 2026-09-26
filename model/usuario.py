from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from werkzeug.security import check_password_hash, generate_password_hash

from model import Base


class Usuario(Base):
    """Uma conta de usuário do Budget Tracker.

    A senha nunca é armazenada em texto puro — apenas o hash gerado por
    `werkzeug.security.generate_password_hash`.
    """
    __tablename__ = 'usuario'

    id = Column("pk_usuario", Integer, primary_key=True)
    nome = Column(String(140), nullable=False)
    email = Column(String(140), unique=True, nullable=False)
    senha_hash = Column(String(256), nullable=False)
    data_insercao = Column(DateTime, default=datetime.now)

    def __init__(self, nome: str, email: str, senha: str):
        """
        Cria um usuário, já convertendo a senha informada em hash.

        Arguments:
            nome: nome do usuário.
            email: e-mail do usuário, usado para login (deve ser único).
            senha: senha em texto puro, convertida em hash antes de ser salva.
        """
        self.nome = nome
        self.email = email
        self.senha_hash = generate_password_hash(senha)

    def verifica_senha(self, senha: str) -> bool:
        """Confere se a senha informada corresponde ao hash salvo"""
        return check_password_hash(self.senha_hash, senha)
