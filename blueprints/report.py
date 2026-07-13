"""Relatório mensal: monta o espelho do mês e dispara o webhook do n8n,
que envia o e-mail (Gmail) com a planilha anexada."""
import base64
from datetime import date
from flask import Blueprint, request, redirect, url_for, flash, render_template
import requests
from models import db, Colaborador, Config as Cfg
from blueprints.auth import admin_req
from servico import calcula_colaborador_mes
from jornada import fmt_hm

bp = Blueprint("report", __name__, url_prefix="/admin/relatorio")

MESES = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
         "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]


def _mes_anterior():
    hoje = date.today()
    return (hoje.year - 1, 12) if hoje.month == 1 else (hoje.year, hoje.month - 1)


def envia_relatorio_mensal(ano=None, mes=None):
    """Monta e dispara o relatório. Retorna (ok:bool, mensagem:str)."""
    from blueprints.export import gera_xlsx
    if ano is None or mes is None:
        ano, mes = _mes_anterior()

    webhook = Cfg.get("n8n_webhook_url", "")
    email = Cfg.get("relatorio_email", "")
    if not webhook:
        return False, "Webhook do n8n não configurado (Configurações)."

    colaboradores = Colaborador.query.filter_by(ativo=True).order_by(Colaborador.nome).all()
    if not colaboradores:
        return False, "Nenhum colaborador ativo."

    resumo = []
    for c in colaboradores:
        _, t = calcula_colaborador_mes(c, ano, mes)
        resumo.append({
            "colaborador": c.nome,
            "horas_trabalhadas": fmt_hm(t["liquido_min"]),
            "he_total": fmt_hm(t["he_total_min"]),
            "he_pagavel": fmt_hm(t["he_pagavel_min"]),
            "banco_horas": fmt_hm(t["banco_min"]),
            "atrasos": fmt_hm(t["atraso_min"]),
            "faltas": t["faltas"],
        })

    buf = gera_xlsx(colaboradores, ano, mes)
    arquivo_b64 = base64.b64encode(buf.getvalue()).decode()
    filename = f"espelho_{MESES[mes].lower()}_{ano}.xlsx"

    payload = {
        "email_destino": email,
        "assunto": f"Espelho de Ponto — {MESES[mes]}/{ano}",
        "mes": MESES[mes], "ano": ano,
        "resumo": resumo,
        "arquivo_nome": filename,
        "arquivo_base64": arquivo_b64,
    }
    try:
        resp = requests.post(webhook, json=payload, timeout=30)
        resp.raise_for_status()
        return True, f"Relatório de {MESES[mes]}/{ano} enviado ao n8n."
    except Exception as e:
        return False, f"Falha ao chamar o n8n: {e}"


@bp.route("/", methods=["GET"])
@admin_req
def painel():
    ano, mes = _mes_anterior()
    return render_template("admin/relatorio.html", ano=ano, mes=mes,
                           mes_nome=MESES[mes],
                           webhook=Cfg.get("n8n_webhook_url", ""),
                           email=Cfg.get("relatorio_email", ""))


@bp.route("/enviar", methods=["POST"])
@admin_req
def enviar():
    ano = request.form.get("ano")
    mes = request.form.get("mes")
    ano = int(ano) if ano else None
    mes = int(mes) if mes else None
    ok, msg = envia_relatorio_mensal(ano, mes)
    flash(msg, "ok" if ok else "erro")
    return redirect(url_for("report.painel"))
