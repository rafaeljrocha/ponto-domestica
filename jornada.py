"""Motor de cálculo de jornada — parâmetros da LC 150/2015 (empregado doméstico).

IMPORTANTE (premissas, para o Rafael validar):
- Hora extra (HE) é calculada como tempo trabalhado ALÉM da jornada prevista na
  regra do dia (o "combinado"). É a métrica mais útil para controle interno.
  Se preferir o critério estrito de "além de 8h/dia", troque JORNADA_NORMAL_ESTRITA
  para True em config (chave: 'he_criterio_8h').
- Trabalho em domingo ou feriado é classificado como HE 100%; nos demais dias, 50%.
- O intervalo é PRÉ-ASSINALADO: descontado automaticamente do tempo bruto quando
  a jornada bruta supera 'intervalo_min' + limiar mínimo.
- Adicional noturno (20%, janela 22h–05h, hora reduzida de 52'30") só é computado
  se ligado em config ('adicional_noturno' = 'on').
- Banco de horas: no mês, as primeiras 40h de HE são "pagáveis" e o excedente vai
  para banco (compensável em até 1 ano — LC 150 art. 2º §§4º-6º). O saldo acumulado
  entre meses NÃO é somado automaticamente nesta versão (é apresentado mês a mês).
"""
import math
from datetime import datetime, date, time, timedelta

MIN_8H = 8 * 60            # jornada diária de referência (minutos)
HE_40H = 40 * 60          # limite mensal de HE "pagável" antes do banco
FATOR_NOTURNO = 60 / 52.5  # hora noturna reduzida (52'30")
NOITE_INI = time(22, 0)
NOITE_FIM = time(5, 0)


# --------------------------------------------------------------------------- #
# Geofence
# --------------------------------------------------------------------------- #
def haversine_m(lat1, lon1, lat2, lon2):
    """Distância em metros entre dois pontos (fórmula de Haversine)."""
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def dentro_da_area(lat, lon, local):
    """Retorna (dentro:bool, distancia_m:float)."""
    if lat is None or lon is None or local is None:
        return False, None
    d = haversine_m(lat, lon, local.latitude, local.longitude)
    return d <= local.raio_efetivo, round(d, 1)


# --------------------------------------------------------------------------- #
# Auxiliares de tempo
# --------------------------------------------------------------------------- #
def _hhmm_para_min(hhmm):
    try:
        h, m = hhmm.split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return 0


def _minutos_noturnos(ini: datetime, fim: datetime):
    """Minutos do intervalo [ini, fim) que caem na janela noturna 22h–05h."""
    if fim <= ini:
        return 0
    total = 0
    cursor = ini
    # varre em blocos diários para tratar viradas de meia-noite
    while cursor < fim:
        prox_meia_noite = datetime.combine(cursor.date() + timedelta(days=1), time(0, 0))
        bloco_fim = min(fim, prox_meia_noite)
        # janela 22:00–24:00 do dia de 'cursor'
        j1_ini = datetime.combine(cursor.date(), NOITE_INI)
        j1_fim = prox_meia_noite
        total += _overlap(cursor, bloco_fim, j1_ini, j1_fim)
        # janela 00:00–05:00 do dia de 'cursor'
        j2_ini = datetime.combine(cursor.date(), time(0, 0))
        j2_fim = datetime.combine(cursor.date(), NOITE_FIM)
        total += _overlap(cursor, bloco_fim, j2_ini, j2_fim)
        cursor = bloco_fim
    return int(total / 60)


def _overlap(a_ini, a_fim, b_ini, b_fim):
    """Segundos de sobreposição entre dois intervalos."""
    ini = max(a_ini, b_ini)
    fim = min(a_fim, b_fim)
    return max(0, (fim - ini).total_seconds())


# --------------------------------------------------------------------------- #
# Cálculo diário
# --------------------------------------------------------------------------- #
def pares(registros):
    """Ordena registros do dia e forma pares (entrada, saída).
    Retorna (lista_de_pares, aberto:bool). 'aberto' = número ímpar de marcações."""
    regs = sorted(registros, key=lambda r: r.momento)
    ps, aberto = [], False
    i = 0
    while i < len(regs):
        if i + 1 < len(regs):
            ps.append((regs[i].momento, regs[i + 1].momento))
            i += 2
        else:
            aberto = True
            i += 1
    return ps, aberto


def calcula_dia(dia, registros_dia, regra, is_feriado, is_abonado,
                criterio_8h=False, usa_noturno=False, conta_dia=True):
    """Calcula os indicadores de um dia para um colaborador.

    registros_dia : lista de Registro daquele dia
    regra         : Regra do dia da semana (ou None)
    is_feriado    : bool
    is_abonado    : bool (férias/folga cobrindo o dia)
    conta_dia     : se False (ex.: dia anterior ao cadastro), não gera falta/atraso
    """
    r = {
        "dia": dia, "trabalhou": bool(registros_dia),
        "bruto_min": 0, "intervalo_min": 0, "liquido_min": 0,
        "atraso_min": 0, "falta": False, "abonado": is_abonado,
        "feriado": is_feriado, "aberto": False,
        "he50_min": 0, "he100_min": 0, "noturno_min": 0,
        "previsto_min": 0, "entrada_real": None,
    }

    prev_trab = bool(regra and regra.trabalha)
    intervalo = regra.intervalo_min if regra else 0
    previsto_liq = 0
    if prev_trab:
        previsto_liq = max(0, _hhmm_para_min(regra.saida_prevista)
                           - _hhmm_para_min(regra.entrada_prevista) - intervalo)
    r["previsto_min"] = previsto_liq

    ps, aberto = pares(registros_dia)
    r["aberto"] = aberto

    if not ps:
        # sem marcações: falta apenas se era dia previsto, não abonado e o dia "conta"
        if prev_trab and not is_abonado and not is_feriado and conta_dia:
            r["falta"] = True
        return r

    bruto = 0
    noturno = 0
    for ini, fim in ps:
        bruto += (fim - ini).total_seconds() / 60
        if usa_noturno:
            noturno += _minutos_noturnos(ini, fim)
    bruto = int(bruto)

    # desconto do intervalo pré-assinalado (só se a jornada comportar)
    desc = intervalo if bruto > (previsto_liq if previsto_liq else MIN_8H) - 15 else 0
    desc = min(desc, max(0, bruto))
    liquido = max(0, bruto - desc)

    r["bruto_min"] = bruto
    r["intervalo_min"] = desc
    r["liquido_min"] = liquido
    r["noturno_min"] = noturno

    # atraso na entrada
    entrada_real = ps[0][0]
    r["entrada_real"] = entrada_real
    if prev_trab and not is_abonado and conta_dia:
        prev_ent = _hhmm_para_min(regra.entrada_prevista)
        real_ent = entrada_real.hour * 60 + entrada_real.minute
        tol = regra.tolerancia_atraso_min or 0
        if real_ent > prev_ent + tol:
            r["atraso_min"] = real_ent - prev_ent - tol

    # horas extras
    base = MIN_8H if criterio_8h else (previsto_liq if previsto_liq else MIN_8H)
    extra = max(0, liquido - base)
    if extra > 0:
        # domingo (dia_semana 6) ou feriado => 100%
        if is_feriado or dia.weekday() == 6:
            r["he100_min"] = extra
        else:
            r["he50_min"] = extra
    return r


# --------------------------------------------------------------------------- #
# Cálculo mensal (agrega dias + banco de horas)
# --------------------------------------------------------------------------- #
def calcula_mes(dias_calculados):
    """Recebe a lista de dicts de calcula_dia e agrega o mês."""
    tot = {
        "liquido_min": 0, "he50_min": 0, "he100_min": 0, "noturno_min": 0,
        "atraso_min": 0, "faltas": 0, "faltas_abonadas": 0, "dias_trabalhados": 0,
        "he_total_min": 0, "he_pagavel_min": 0, "banco_min": 0, "dias_aberto": 0,
    }
    for d in dias_calculados:
        tot["liquido_min"] += d["liquido_min"]
        tot["he50_min"] += d["he50_min"]
        tot["he100_min"] += d["he100_min"]
        tot["noturno_min"] += d["noturno_min"]
        tot["atraso_min"] += d["atraso_min"]
        if d["falta"]:
            tot["faltas"] += 1
        if d["abonado"] and not d["trabalhou"]:
            tot["faltas_abonadas"] += 1
        if d["trabalhou"]:
            tot["dias_trabalhados"] += 1
        if d["aberto"]:
            tot["dias_aberto"] += 1

    tot["he_total_min"] = tot["he50_min"] + tot["he100_min"]
    tot["he_pagavel_min"] = min(tot["he_total_min"], HE_40H)
    tot["banco_min"] = max(0, tot["he_total_min"] - HE_40H)
    return tot


def fmt_hm(minutos):
    """Formata minutos como 'HHhMM'."""
    minutos = int(minutos or 0)
    sinal = "-" if minutos < 0 else ""
    minutos = abs(minutos)
    return f"{sinal}{minutos // 60}h{minutos % 60:02d}"
