"""Horário local (America/Sao_Paulo), independente do fuso do contêiner.

O contêiner roda em UTC; Maringá é UTC-3. Todas as gravações e comparações de
data/hora do sistema passam por aqui para evitar diferença de fuso.
Retornamos datetimes "naive" (sem tzinfo), já convertidos para o horário local,
para casar com as colunas DateTime existentes e com a exibição via strftime.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Sao_Paulo")


def agora():
    """Horário atual de Maringá, como datetime naive."""
    return datetime.now(TZ).replace(tzinfo=None)


def hoje():
    """Data atual de Maringá."""
    return agora().date()
