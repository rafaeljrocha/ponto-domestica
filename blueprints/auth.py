"""Autenticação: admin (usuário/senha) e colaborador (PIN)."""
from functools import wraps
from flask import (Blueprint, render_template, request, redirect, url_for,
                   session, flash)
from models import db, Admin, Colaborador

bp = Blueprint("auth", __name__)


# --- Decorators ------------------------------------------------------------ #
def admin_req(f):
    @wraps(f)
    def wrap(*a, **kw):
        if not session.get("admin_id"):
            return redirect(url_for("auth.admin_login", next=request.path))
        return f(*a, **kw)
    return wrap


def colab_req(f):
    @wraps(f)
    def wrap(*a, **kw):
        if not session.get("colab_id"):
            return redirect(url_for("auth.colab_login"))
        return f(*a, **kw)
    return wrap


# --- Admin ----------------------------------------------------------------- #
@bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        adm = Admin.query.filter_by(usuario=request.form.get("usuario", "").strip()).first()
        if adm and adm.checa_senha(request.form.get("senha", "")):
            session["admin_id"] = adm.id
            session["admin_nome"] = adm.usuario
            return redirect(request.args.get("next") or url_for("dashboard.painel"))
        flash("Usuário ou senha incorretos.", "erro")
    return render_template("login.html", modo="admin")


@bp.route("/admin/logout")
def admin_logout():
    session.pop("admin_id", None)
    session.pop("admin_nome", None)
    return redirect(url_for("auth.admin_login"))


# --- Colaborador (mobile) -------------------------------------------------- #
@bp.route("/entrar", methods=["GET", "POST"])
def colab_login():
    if request.method == "POST":
        colab = Colaborador.query.filter_by(
            id=request.form.get("colaborador_id"), ativo=True).first()
        if colab and colab.checa_pin(request.form.get("pin", "")):
            session["colab_id"] = colab.id
            session["colab_nome"] = colab.nome
            return redirect(url_for("registro.tela"))
        flash("PIN incorreto.", "erro")
    colaboradores = Colaborador.query.filter_by(ativo=True).order_by(Colaborador.nome).all()
    return render_template("login.html", modo="colab", colaboradores=colaboradores)


@bp.route("/sair")
def colab_logout():
    session.pop("colab_id", None)
    session.pop("colab_nome", None)
    return redirect(url_for("auth.colab_login"))
