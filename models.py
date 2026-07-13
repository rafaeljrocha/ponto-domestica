"""Modelos de dados.

Entidades:
- Admin          : usuário do painel (empregador).
- Local          : ponto geográfico do trabalho (geofence editável).
- Colaborador    : empregado doméstico / babá.
- Regra          : jornada prevista por dia da semana (1 linha por dia).
- Registro       : cada toque no botão (entrada/saída), com geolocalização.
- Excecao        : férias e folgas (abonam falta/atraso), por colaborador.
- Feriado        : feriados (nacional/PR/Curitiba/personalizado), globais.
- Ajuste         : log de auditoria de alterações manuais em registros.
- Config         : pares chave/valor para parâmetros do sistema.
"""
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Admin(db.Model):
    __tablename__ = "admin"
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(60), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)

    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def checa_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)


class Local(db.Model):
    __tablename__ = "local"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    endereco = db.Column(db.String(255), default="")
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    raio_m = db.Column(db.Integer, default=150)
    tolerancia_m = db.Column(db.Integer, default=80)
    ativo = db.Column(db.Boolean, default=True)

    colaboradores = db.relationship("Colaborador", backref="local", lazy=True)

    @property
    def raio_efetivo(self):
        return (self.raio_m or 0) + (self.tolerancia_m or 0)


class Colaborador(db.Model):
    __tablename__ = "colaborador"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    funcao = db.Column(db.String(80), default="")          # ex.: Empregada doméstica, Babá
    tipo = db.Column(db.String(20), default="mensalista")   # mensalista | parcial | 12x36
    pin_hash = db.Column(db.String(255), nullable=False)    # PIN de acesso no celular
    salario_base = db.Column(db.Float, default=0.0)         # opcional, para valorizar HE
    exige_selfie = db.Column(db.Boolean, default=False)
    ativo = db.Column(db.Boolean, default=True)
    local_id = db.Column(db.Integer, db.ForeignKey("local.id"))
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    regras = db.relationship("Regra", backref="colaborador", lazy=True,
                             cascade="all, delete-orphan")
    registros = db.relationship("Registro", backref="colaborador", lazy=True,
                                cascade="all, delete-orphan")
    excecoes = db.relationship("Excecao", backref="colaborador", lazy=True,
                               cascade="all, delete-orphan")

    def set_pin(self, pin):
        self.pin_hash = generate_password_hash(str(pin))

    def checa_pin(self, pin):
        return check_password_hash(self.pin_hash, str(pin))


class Regra(db.Model):
    """Jornada prevista. Uma linha por dia da semana (0=segunda ... 6=domingo)."""
    __tablename__ = "regra"
    id = db.Column(db.Integer, primary_key=True)
    colaborador_id = db.Column(db.Integer, db.ForeignKey("colaborador.id"), nullable=False)
    dia_semana = db.Column(db.Integer, nullable=False)      # 0=seg ... 6=dom
    trabalha = db.Column(db.Boolean, default=True)
    entrada_prevista = db.Column(db.String(5), default="08:00")  # HH:MM
    saida_prevista = db.Column(db.String(5), default="17:00")
    intervalo_min = db.Column(db.Integer, default=60)      # pré-assinalado (descontado)
    tolerancia_atraso_min = db.Column(db.Integer, default=10)

    __table_args__ = (db.UniqueConstraint("colaborador_id", "dia_semana"),)


class Registro(db.Model):
    __tablename__ = "registro"
    id = db.Column(db.Integer, primary_key=True)
    colaborador_id = db.Column(db.Integer, db.ForeignKey("colaborador.id"), nullable=False)
    momento = db.Column(db.DateTime, nullable=False, default=datetime.now)
    tipo = db.Column(db.String(10), default="entrada")     # entrada | saida (derivado)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    distancia_m = db.Column(db.Float)                       # até o local do colaborador
    dentro_area = db.Column(db.Boolean, default=True)
    selfie_path = db.Column(db.String(255))
    origem = db.Column(db.String(12), default="mobile")    # mobile | ajuste
    comprovante = db.Column(db.String(20))                 # código do comprovante

    @property
    def dia(self):
        return self.momento.date()


class Excecao(db.Model):
    """Férias e folgas por colaborador. Abonam atraso/falta no período."""
    __tablename__ = "excecao"
    id = db.Column(db.Integer, primary_key=True)
    colaborador_id = db.Column(db.Integer, db.ForeignKey("colaborador.id"), nullable=False)
    tipo = db.Column(db.String(12), nullable=False)        # ferias | folga
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date, nullable=False)
    descricao = db.Column(db.String(200), default="")
    abona = db.Column(db.Boolean, default=True)


class Feriado(db.Model):
    """Feriados globais (aplicam a todos). Trabalho no feriado => HE 100%."""
    __tablename__ = "feriado"
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False, unique=True)
    nome = db.Column(db.String(120), nullable=False)
    escopo = db.Column(db.String(20), default="nacional")  # nacional | estadual | municipal | custom


class Ajuste(db.Model):
    """Trilha de auditoria de alterações manuais."""
    __tablename__ = "ajuste"
    id = db.Column(db.Integer, primary_key=True)
    momento = db.Column(db.DateTime, default=datetime.utcnow)
    usuario = db.Column(db.String(60))
    acao = db.Column(db.String(30))                        # criar | editar | excluir
    alvo = db.Column(db.String(60))                        # ex.: registro:123
    justificativa = db.Column(db.String(255))
    antes = db.Column(db.Text)
    depois = db.Column(db.Text)


class Config(db.Model):
    __tablename__ = "config"
    chave = db.Column(db.String(60), primary_key=True)
    valor = db.Column(db.String(255))

    @staticmethod
    def get(chave, padrao=None):
        c = db.session.get(Config, chave)
        return c.valor if c else padrao

    @staticmethod
    def set(chave, valor):
        c = db.session.get(Config, chave)
        if c:
            c.valor = str(valor)
        else:
            db.session.add(Config(chave=chave, valor=str(valor)))
        db.session.commit()
