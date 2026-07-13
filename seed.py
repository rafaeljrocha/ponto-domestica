"""Semente inicial do banco: admin, local base, feriados e config padrão.

Roda de forma idempotente a cada boot (só cria o que ainda não existe).
"""
from datetime import date, timedelta
from models import db, Admin, Local, Feriado, Config as Cfg
from config import Config as Cfg_env


def _pascoa(ano):
    """Data da Páscoa (algoritmo de Meeus/Butcher)."""
    a = ano % 19
    b = ano // 100
    c = ano % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    return date(ano, mes, dia)


def feriados_do_ano(ano):
    """Lista (data, nome, escopo). Fixos nacionais + móveis + PR/Maringá.
    Ajuste os municipais/estaduais conforme sua realidade no painel."""
    p = _pascoa(ano)
    itens = [
        (date(ano, 1, 1), "Confraternização Universal", "nacional"),
        (p - timedelta(days=48), "Carnaval (segunda)", "nacional"),
        (p - timedelta(days=47), "Carnaval (terça)", "nacional"),
        (p - timedelta(days=2), "Sexta-feira Santa", "nacional"),
        (date(ano, 4, 21), "Tiradentes", "nacional"),
        (date(ano, 5, 1), "Dia do Trabalho", "nacional"),
        (p + timedelta(days=60), "Corpus Christi", "nacional"),
        (date(ano, 9, 7), "Independência", "nacional"),
        (date(ano, 10, 12), "Nossa Senhora Aparecida", "nacional"),
        (date(ano, 11, 2), "Finados", "nacional"),
        (date(ano, 11, 15), "Proclamação da República", "nacional"),
        (date(ano, 11, 20), "Consciência Negra", "nacional"),
        (date(ano, 12, 25), "Natal", "nacional"),
        # --- Editáveis: estaduais/municipais ---
        (date(ano, 5, 10), "Aniversário de Maringá", "municipal"),
        (date(ano, 12, 19), "Emancipação do Paraná", "estadual"),
    ]
    return itens


def semeia_inicial(app):
    # Admin
    if not Admin.query.first():
        adm = Admin(usuario=Cfg_env.ADMIN_USUARIO)
        adm.set_senha(Cfg_env.ADMIN_SENHA)
        db.session.add(adm)

    # Local base
    if not Local.query.first():
        db.session.add(Local(
            nome=Cfg_env.LOCAL_PADRAO_NOME,
            endereco=Cfg_env.LOCAL_PADRAO_ENDERECO,
            latitude=Cfg_env.LOCAL_PADRAO_LAT,
            longitude=Cfg_env.LOCAL_PADRAO_LNG,
            raio_m=Cfg_env.LOCAL_PADRAO_RAIO_M,
            tolerancia_m=Cfg_env.LOCAL_PADRAO_TOLERANCIA_M,
        ))

    # Feriados (ano atual e próximo)
    anos = {date.today().year, date.today().year + 1}
    for ano in anos:
        for d, nome, escopo in feriados_do_ano(ano):
            if not Feriado.query.filter_by(data=d).first():
                db.session.add(Feriado(data=d, nome=nome, escopo=escopo))

    db.session.commit()

    # Config padrão
    defaults = {
        "relatorio_dia": "1",
        "fechamento": "calendario",
        "he_criterio_8h": "off",
        "adicional_noturno": "off",
        "n8n_webhook_url": Cfg_env.N8N_WEBHOOK_URL,
        "relatorio_email": Cfg_env.RELATORIO_EMAIL,
    }
    for k, v in defaults.items():
        if Cfg.get(k) is None:
            Cfg.set(k, v)
