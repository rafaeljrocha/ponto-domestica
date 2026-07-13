"""Registro de ponto (mobile). Botão único inteligente: alterna entrada/saída."""
import os
import base64
import secrets
from datetime import datetime, date
from flask import (Blueprint, render_template, request, jsonify, session)
from models import db, Colaborador, Registro
from jornada import dentro_da_area
from blueprints.auth import colab_req
from config import Config

bp = Blueprint("registro", __name__, url_prefix="/registro")


def _registros_hoje(colab_id):
    hoje = date.today()
    ini = datetime.combine(hoje, datetime.min.time())
    fim = datetime.combine(hoje, datetime.max.time())
    return (Registro.query
            .filter(Registro.colaborador_id == colab_id,
                    Registro.momento >= ini, Registro.momento <= fim)
            .order_by(Registro.momento).all())


@bp.route("/")
@colab_req
def tela():
    colab = db.session.get(Colaborador, session["colab_id"])
    regs = _registros_hoje(colab.id)
    proximo = "saida" if len(regs) % 2 == 1 else "entrada"
    return render_template("registro.html", colab=colab, regs=regs,
                           proximo=proximo, local=colab.local)


@bp.route("/marcar", methods=["POST"])
@colab_req
def marcar():
    colab = db.session.get(Colaborador, session["colab_id"])
    dados = request.get_json(silent=True) or {}

    lat = dados.get("lat")
    lng = dados.get("lng")
    lat = float(lat) if lat is not None else None
    lng = float(lng) if lng is not None else None

    dentro, dist = dentro_da_area(lat, lng, colab.local)

    regs = _registros_hoje(colab.id)
    tipo = "saida" if len(regs) % 2 == 1 else "entrada"

    # selfie opcional (data URL base64)
    selfie_path = None
    selfie = dados.get("selfie")
    if colab.exige_selfie and selfie and selfie.startswith("data:image"):
        try:
            cabecalho, b64 = selfie.split(",", 1)
            nome = f"{colab.id}_{datetime.now():%Y%m%d%H%M%S}.jpg"
            caminho = os.path.join(Config.UPLOAD_DIR, nome)
            with open(caminho, "wb") as fp:
                fp.write(base64.b64decode(b64))
            selfie_path = nome
        except Exception:
            selfie_path = None

    codigo = secrets.token_hex(4).upper()
    reg = Registro(
        colaborador_id=colab.id, momento=datetime.now(), tipo=tipo,
        latitude=lat, longitude=lng, distancia_m=dist, dentro_area=dentro,
        selfie_path=selfie_path, origem="mobile", comprovante=codigo,
    )
    db.session.add(reg)
    db.session.commit()

    return jsonify({
        "ok": True,
        "tipo": tipo,
        "horario": reg.momento.strftime("%d/%m/%Y %H:%M:%S"),
        "dentro_area": dentro,
        "distancia_m": dist,
        "comprovante": codigo,
        "colaborador": colab.nome,
    })
