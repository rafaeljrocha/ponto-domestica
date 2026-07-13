"""Configuração central da aplicação.

Todos os parâmetros sensíveis ou de ambiente vêm de variáveis de ambiente,
para nada ficar hardcoded no repositório (segurança). Os defaults servem
para rodar localmente.
"""
import os


class Config:
    # --- Flask / segurança ---
    SECRET_KEY = os.environ.get("SECRET_KEY", "troque-esta-chave-no-easypanel")

    # --- Banco ---
    # No EasyPanel, aponte para o volume persistente (ex.: /app/data/ponto.db)
    _db_path = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "data", "ponto.db"))
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", f"sqlite:///{_db_path}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Admin inicial (semente) ---
    ADMIN_USUARIO = os.environ.get("ADMIN_USUARIO", "rafael")
    ADMIN_SENHA = os.environ.get("ADMIN_SENHA", "trocar123")

    # --- Integração n8n (relatório mensal) ---
    N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL", "")
    RELATORIO_EMAIL = os.environ.get("RELATORIO_EMAIL", "rafaeljrocha@gmail.com")

    # --- Upload de selfies ---
    UPLOAD_DIR = os.environ.get("UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "data", "selfies"))
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB

    # --- Localização base padrão (Av. Cerro Azul, 2649, Casa G23) ---
    LOCAL_PADRAO_NOME = "Residência – Casa G23"
    LOCAL_PADRAO_ENDERECO = "Av. Cerro Azul, 2649, Casa G23, Maringá/PR"
    LOCAL_PADRAO_LAT = -23.451737
    LOCAL_PADRAO_LNG = -51.928168
    LOCAL_PADRAO_RAIO_M = 150      # raio da cerca
    LOCAL_PADRAO_TOLERANCIA_M = 80  # folga adicional para imprecisão do GPS
