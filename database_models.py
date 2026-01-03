# Importamos as ferramentas necessárias do SQLAlchemy
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, Date
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import date

# 1. Configuração do Banco de Dados
# Para este teste, usamos SQLite (um ficheiro local).
# Para mudar para PostgreSQL no futuro, basta alterar esta linha de conexão.
DATABASE_URL = "sqlite:///./prologos_mvp.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. Definição das Tabelas (Modelos)


class Tribunal(Base):
    __tablename__ = "tribunais"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True)  # Ex: TJSP, TJRJ
    estado = Column(String)  # Ex: SP, RJ

    # Relação: Um tribunal tem muitos juízes
    juizes = relationship("Juiz", back_populates="tribunal")


class Juiz(Base):
    __tablename__ = "juizes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True)  # Ex: Dr. Fulano de Tal
    vara = Column(String)  # Ex: 5ª Vara Cível
    tribunal_id = Column(Integer, ForeignKey("tribunais.id"))

    # Relações
    tribunal = relationship("Tribunal", back_populates="juizes")
    decisoes = relationship("Decisao", back_populates="juiz")


class Decisao(Base):
    __tablename__ = "decisoes"

    id = Column(Integer, primary_key=True, index=True)
    numero_processo = Column(String, unique=True, index=True)
    texto_decisao = Column(Text)  # O texto completo da sentença (para a IA ler depois)
    resultado = Column(String)  # Ex: Procedente, Improcedente (Normalizado)
    tema = Column(String)  # Ex: Responsabilidade Civil
    data_decisao = Column(Date)

    juiz_id = Column(Integer, ForeignKey("juizes.id"))

    # Relação: Uma decisão pertence a um juiz
    juiz = relationship("Juiz", back_populates="decisoes")


# 3. Criação das tabelas
# Este bloco cria o ficheiro do banco de dados automaticamente se ele não existir
if __name__ == "__main__":
    print("A criar a base de dados do PRÓLOGOS...")
    Base.metadata.create_all(bind=engine)
    print("Sucesso! O arquivo 'prologos_mvp.db' foi criado com as tabelas.")
