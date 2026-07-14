"""Serviço de agregação: junta registros + regras + exceções + feriados
e roda o motor de jornada para um colaborador em um mês."""
import calendar
from datetime import date, datetime
from models import db, Registro, Regra, Excecao, Feriado, Config as Cfg
from tempo import hoje as _hoje
import jornada


def _abonado(colab_id, dia):
    return (Excecao.query.filter(
        Excecao.colaborador_id == colab_id,
        Excecao.abona.is_(True),
        Excecao.data_inicio <= dia,
        Excecao.data_fim >= dia).first() is not None)


def calcula_colaborador_mes(colab, ano, mes):
    """Retorna (lista_dias, totais). Cada 'dia' é o dict de jornada.calcula_dia."""
    criterio_8h = Cfg.get("he_criterio_8h", "off") == "on"
    usa_noturno = Cfg.get("adicional_noturno", "off") == "on"

    regras = {r.dia_semana: r for r in colab.regras}
    feriados = {f.data for f in Feriado.query.filter(
        Feriado.data >= date(ano, mes, 1),
        Feriado.data <= date(ano, mes, calendar.monthrange(ano, mes)[1])).all()}

    ini = datetime(ano, mes, 1)
    fim = datetime(ano, mes, calendar.monthrange(ano, mes)[1], 23, 59, 59)
    registros = (Registro.query.filter(
        Registro.colaborador_id == colab.id,
        Registro.momento >= ini, Registro.momento <= fim)
        .order_by(Registro.momento).all())

    por_dia = {}
    for r in registros:
        por_dia.setdefault(r.momento.date(), []).append(r)

    cadastro = colab.criado_em.date() if colab.criado_em else date(1900, 1, 1)
    hoje = _hoje()

    dias = []
    for d in range(1, calendar.monthrange(ano, mes)[1] + 1):
        dia = date(ano, mes, d)
        regra = regras.get(dia.weekday())
        # não gera falta/atraso antes do cadastro nem para dias futuros
        conta = cadastro <= dia <= hoje
        dc = jornada.calcula_dia(
            dia, por_dia.get(dia, []), regra,
            is_feriado=dia in feriados,
            is_abonado=_abonado(colab.id, dia),
            criterio_8h=criterio_8h, usa_noturno=usa_noturno, conta_dia=conta)
        dias.append(dc)

    totais = jornada.calcula_mes(dias)
    return dias, totais
