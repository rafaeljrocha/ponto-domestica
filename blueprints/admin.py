"""Painel administrativo (empregador)."""
import json
from datetime import datetime, date
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, session)
from models import db, Colaborador, Local, Regra, Registro, Excecao, Feriado, Ajuste, Config as Cfg
from blueprints.auth import admin_req

bp = Blueprint("admin", __name__, url_prefix="/admin")

DIAS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


def _log(acao, alvo, justificativa="", antes=None, depois=None):
    db.session.add(Ajuste(
        usuario=session.get("admin_nome", "admin"), acao=acao, alvo=alvo,
        justificativa=justificativa,
        antes=json.dumps(antes, default=str, ensure_ascii=False) if antes else None,
        depois=json.dumps(depois, default=str, ensure_ascii=False) if depois else None,
    ))


# --------------------------------------------------------------------------- #
# Colaboradores
# --------------------------------------------------------------------------- #
@bp.route("/colaboradores")
@admin_req
def colaboradores():
    lista = Colaborador.query.order_by(Colaborador.ativo.desc(), Colaborador.nome).all()
    return render_template("admin/colaboradores.html", colaboradores=lista)


@bp.route("/colaboradores/novo", methods=["GET", "POST"])
@admin_req
def colaborador_novo():
    if request.method == "POST":
        c = Colaborador(
            nome=request.form["nome"].strip(),
            funcao=request.form.get("funcao", "").strip(),
            tipo=request.form.get("tipo", "mensalista"),
            salario_base=float(request.form.get("salario_base") or 0),
            exige_selfie=bool(request.form.get("exige_selfie")),
            local_id=int(request.form["local_id"]),
            ativo=True,
        )
        c.set_pin(request.form["pin"].strip())
        db.session.add(c)
        db.session.flush()
        _cria_ou_atualiza_regras(c)
        _log("criar", f"colaborador:{c.id}", depois={"nome": c.nome})
        db.session.commit()
        flash(f"Colaborador {c.nome} cadastrado.", "ok")
        return redirect(url_for("admin.colaboradores"))
    locais = Local.query.filter_by(ativo=True).all()
    return render_template("admin/colaborador_form.html", colab=None,
                           locais=locais, dias=DIAS, regras=None)


@bp.route("/colaboradores/<int:cid>/editar", methods=["GET", "POST"])
@admin_req
def colaborador_editar(cid):
    c = db.session.get(Colaborador, cid) or abort_404()
    if request.method == "POST":
        c.nome = request.form["nome"].strip()
        c.funcao = request.form.get("funcao", "").strip()
        c.tipo = request.form.get("tipo", "mensalista")
        c.salario_base = float(request.form.get("salario_base") or 0)
        c.exige_selfie = bool(request.form.get("exige_selfie"))
        c.local_id = int(request.form["local_id"])
        if request.form.get("pin", "").strip():
            c.set_pin(request.form["pin"].strip())
        _cria_ou_atualiza_regras(c)
        _log("editar", f"colaborador:{c.id}", depois={"nome": c.nome})
        db.session.commit()
        flash("Alterações salvas.", "ok")
        return redirect(url_for("admin.colaboradores"))
    locais = Local.query.filter_by(ativo=True).all()
    regras = {r.dia_semana: r for r in c.regras}
    return render_template("admin/colaborador_form.html", colab=c,
                           locais=locais, dias=DIAS, regras=regras)


@bp.route("/colaboradores/<int:cid>/toggle", methods=["POST"])
@admin_req
def colaborador_toggle(cid):
    c = db.session.get(Colaborador, cid) or abort_404()
    c.ativo = not c.ativo
    db.session.commit()
    flash(f"{c.nome} {'ativado' if c.ativo else 'inativado'}.", "ok")
    return redirect(url_for("admin.colaboradores"))


@bp.route("/colaboradores/<int:cid>/excluir", methods=["POST"])
@admin_req
def colaborador_excluir(cid):
    c = db.session.get(Colaborador, cid) or abort_404()
    nome = c.nome
    _log("excluir", f"colaborador:{cid}", justificativa=request.form.get("justificativa", ""),
         antes={"nome": nome})
    db.session.delete(c)
    db.session.commit()
    flash(f"Colaborador {nome} e seus dados foram excluídos.", "ok")
    return redirect(url_for("admin.colaboradores"))


def _cria_ou_atualiza_regras(c):
    existentes = {r.dia_semana: r for r in c.regras}
    for d in range(7):
        r = existentes.get(d) or Regra(colaborador_id=c.id, dia_semana=d)
        r.trabalha = bool(request.form.get(f"dia_{d}_trabalha"))
        r.entrada_prevista = request.form.get(f"dia_{d}_entrada", "08:00") or "08:00"
        r.saida_prevista = request.form.get(f"dia_{d}_saida", "17:00") or "17:00"
        r.intervalo_min = int(request.form.get(f"dia_{d}_intervalo") or 0)
        r.tolerancia_atraso_min = int(request.form.get(f"dia_{d}_tolerancia") or 0)
        if d not in existentes:
            db.session.add(r)


# --------------------------------------------------------------------------- #
# Locais (geofence)
# --------------------------------------------------------------------------- #
@bp.route("/locais", methods=["GET", "POST"])
@admin_req
def locais():
    if request.method == "POST":
        lat, lng = _parse_coord(request.form.get("coord", ""))
        if lat is None:
            lat = float(request.form.get("latitude"))
            lng = float(request.form.get("longitude"))
        l = Local(
            nome=request.form["nome"].strip(),
            endereco=request.form.get("endereco", "").strip(),
            latitude=lat, longitude=lng,
            raio_m=int(request.form.get("raio_m") or 150),
            tolerancia_m=int(request.form.get("tolerancia_m") or 80),
        )
        db.session.add(l)
        db.session.commit()
        flash("Local cadastrado.", "ok")
        return redirect(url_for("admin.locais"))
    return render_template("admin/locais.html", locais=Local.query.all())


@bp.route("/locais/<int:lid>/editar", methods=["POST"])
@admin_req
def local_editar(lid):
    l = db.session.get(Local, lid) or abort_404()
    lat, lng = _parse_coord(request.form.get("coord", ""))
    l.nome = request.form["nome"].strip()
    l.endereco = request.form.get("endereco", "").strip()
    if lat is not None:
        l.latitude, l.longitude = lat, lng
    l.raio_m = int(request.form.get("raio_m") or l.raio_m)
    l.tolerancia_m = int(request.form.get("tolerancia_m") or l.tolerancia_m)
    l.ativo = bool(request.form.get("ativo"))
    db.session.commit()
    flash("Local atualizado.", "ok")
    return redirect(url_for("admin.locais"))


def _parse_coord(texto):
    """Aceita 'lat, lng' colado do Google Maps. Retorna (lat, lng) ou (None, None)."""
    try:
        parte = texto.replace(" ", "").split(",")
        if len(parte) == 2:
            return float(parte[0]), float(parte[1])
    except Exception:
        pass
    return None, None


# --------------------------------------------------------------------------- #
# Exceções (férias / folgas)
# --------------------------------------------------------------------------- #
@bp.route("/excecoes", methods=["GET", "POST"])
@admin_req
def excecoes():
    if request.method == "POST":
        e = Excecao(
            colaborador_id=int(request.form["colaborador_id"]),
            tipo=request.form["tipo"],
            data_inicio=datetime.strptime(request.form["data_inicio"], "%Y-%m-%d").date(),
            data_fim=datetime.strptime(request.form["data_fim"], "%Y-%m-%d").date(),
            descricao=request.form.get("descricao", "").strip(),
            abona=True,
        )
        db.session.add(e)
        db.session.commit()
        flash("Exceção registrada.", "ok")
        return redirect(url_for("admin.excecoes"))
    colaboradores = Colaborador.query.filter_by(ativo=True).all()
    lista = (Excecao.query.order_by(Excecao.data_inicio.desc()).all())
    mapa = {c.id: c.nome for c in Colaborador.query.all()}
    return render_template("admin/excecoes.html", excecoes=lista,
                           colaboradores=colaboradores, mapa=mapa)


@bp.route("/excecoes/<int:eid>/excluir", methods=["POST"])
@admin_req
def excecao_excluir(eid):
    e = db.session.get(Excecao, eid) or abort_404()
    db.session.delete(e)
    db.session.commit()
    flash("Exceção removida.", "ok")
    return redirect(url_for("admin.excecoes"))


# --------------------------------------------------------------------------- #
# Feriados
# --------------------------------------------------------------------------- #
@bp.route("/feriados", methods=["GET", "POST"])
@admin_req
def feriados():
    if request.method == "POST":
        d = datetime.strptime(request.form["data"], "%Y-%m-%d").date()
        if not Feriado.query.filter_by(data=d).first():
            db.session.add(Feriado(data=d, nome=request.form["nome"].strip(),
                                   escopo=request.form.get("escopo", "custom")))
            db.session.commit()
            flash("Feriado adicionado.", "ok")
        else:
            flash("Já existe feriado nessa data.", "erro")
        return redirect(url_for("admin.feriados"))
    lista = Feriado.query.order_by(Feriado.data).all()
    return render_template("admin/feriados.html", feriados=lista)


@bp.route("/feriados/<int:fid>/excluir", methods=["POST"])
@admin_req
def feriado_excluir(fid):
    f = db.session.get(Feriado, fid) or abort_404()
    db.session.delete(f)
    db.session.commit()
    flash("Feriado removido.", "ok")
    return redirect(url_for("admin.feriados"))


# --------------------------------------------------------------------------- #
# Ajustes manuais de registro (com auditoria)
# --------------------------------------------------------------------------- #
@bp.route("/ajustes", methods=["GET", "POST"])
@admin_req
def ajustes():
    if request.method == "POST":
        acao = request.form.get("acao")
        justificativa = request.form.get("justificativa", "").strip()
        if not justificativa:
            flash("Justificativa é obrigatória para ajuste manual.", "erro")
            return redirect(url_for("admin.ajustes"))

        if acao == "criar":
            momento = datetime.strptime(request.form["momento"], "%Y-%m-%dT%H:%M")
            reg = Registro(
                colaborador_id=int(request.form["colaborador_id"]),
                momento=momento, tipo=request.form.get("tipo", "entrada"),
                origem="ajuste", dentro_area=True, comprovante="MANUAL",
            )
            db.session.add(reg)
            db.session.flush()
            _log("criar", f"registro:{reg.id}", justificativa,
                 depois={"momento": str(momento), "tipo": reg.tipo})
        elif acao == "excluir":
            reg = db.session.get(Registro, int(request.form["registro_id"]))
            if reg:
                _log("excluir", f"registro:{reg.id}", justificativa,
                     antes={"momento": str(reg.momento), "tipo": reg.tipo})
                db.session.delete(reg)
        db.session.commit()
        flash("Ajuste aplicado e registrado na auditoria.", "ok")
        return redirect(url_for("admin.ajustes"))

    colaboradores = Colaborador.query.filter_by(ativo=True).all()
    recentes = Registro.query.order_by(Registro.momento.desc()).limit(40).all()
    mapa = {c.id: c.nome for c in Colaborador.query.all()}
    logs = Ajuste.query.order_by(Ajuste.momento.desc()).limit(30).all()
    return render_template("admin/ajustes.html", colaboradores=colaboradores,
                           recentes=recentes, mapa=mapa, logs=logs)


# --------------------------------------------------------------------------- #
# Configurações
# --------------------------------------------------------------------------- #
@bp.route("/config", methods=["GET", "POST"])
@admin_req
def config():
    chaves = ["relatorio_dia", "fechamento", "he_criterio_8h", "adicional_noturno",
              "n8n_webhook_url", "relatorio_email"]
    if request.method == "POST":
        Cfg.set("relatorio_dia", request.form.get("relatorio_dia", "1"))
        Cfg.set("fechamento", request.form.get("fechamento", "calendario"))
        Cfg.set("he_criterio_8h", "on" if request.form.get("he_criterio_8h") else "off")
        Cfg.set("adicional_noturno", "on" if request.form.get("adicional_noturno") else "off")
        Cfg.set("n8n_webhook_url", request.form.get("n8n_webhook_url", "").strip())
        Cfg.set("relatorio_email", request.form.get("relatorio_email", "").strip())
        flash("Configurações salvas.", "ok")
        return redirect(url_for("admin.config"))
    valores = {k: Cfg.get(k, "") for k in chaves}
    return render_template("admin/config.html", cfg=valores)


def abort_404():
    from flask import abort
    abort(404)
