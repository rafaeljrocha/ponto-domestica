"""Dashboard: métricas principais do mês."""
from datetime import date
from tempo import hoje as _hoje
from flask import Blueprint, render_template, request, jsonify, session
from models import db, Colaborador
from blueprints.auth import admin_req
from servico import calcula_colaborador_mes
from jornada import fmt_hm

bp = Blueprint("dashboard", __name__, url_prefix="/admin")


def _periodo():
    hoje = _hoje()
    ano = int(request.args.get("ano", hoje.year))
    mes = int(request.args.get("mes", hoje.month))
    return ano, mes


@bp.route("/")
@bp.route("/painel")
@admin_req
def painel():
    ano, mes = _periodo()
    colaboradores = Colaborador.query.filter_by(ativo=True).order_by(Colaborador.nome).all()

    linhas = []
    consolidado = {"liquido_min": 0, "he50_min": 0, "he100_min": 0,
                   "noturno_min": 0, "atraso_min": 0, "faltas": 0,
                   "banco_min": 0, "dias_aberto": 0}
    for c in colaboradores:
        _, t = calcula_colaborador_mes(c, ano, mes)
        linhas.append({"colab": c, "t": t})
        for k in consolidado:
            consolidado[k] += t.get(k, 0)

    return render_template("admin/dashboard.html", linhas=linhas,
                           consolidado=consolidado, ano=ano, mes=mes,
                           fmt=fmt_hm, colaboradores=colaboradores)


@bp.route("/colaborador/<int:cid>")
@admin_req
def detalhe(cid):
    ano, mes = _periodo()
    c = db.session.get(Colaborador, cid)
    dias, t = calcula_colaborador_mes(c, ano, mes)
    return render_template("admin/detalhe.html", colab=c, dias=dias, t=t,
                           ano=ano, mes=mes, fmt=fmt_hm)


@bp.route("/api/grafico/<int:cid>")
@admin_req
def api_grafico(cid):
    ano, mes = _periodo()
    c = db.session.get(Colaborador, cid)
    dias, _ = calcula_colaborador_mes(c, ano, mes)
    return jsonify({
        "labels": [d["dia"].strftime("%d") for d in dias],
        "trabalhadas": [round(d["liquido_min"] / 60, 2) for d in dias],
        "he": [round((d["he50_min"] + d["he100_min"]) / 60, 2) for d in dias],
    })
