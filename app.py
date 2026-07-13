"""Ponto Doméstico — controle interno de jornada (LC 150/2015).

App factory Flask. Registra blueprints, inicializa o banco, cria a semente
(admin, local base, feriados) e agenda o envio mensal do relatório via n8n.
"""
import os
from flask import Flask, redirect, url_for
from config import Config
from models import db, Admin, Local, Colaborador, Feriado, Config as Cfg
from seed import semeia_inicial

from blueprints.auth import bp as auth_bp
from blueprints.registro import bp as registro_bp
from blueprints.admin import bp as admin_bp
from blueprints.dashboard import bp as dashboard_bp
from blueprints.export import bp as export_bp
from blueprints.report import bp as report_bp, envia_relatorio_mensal


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(os.path.dirname(Config._db_path), exist_ok=True)
    os.makedirs(Config.UPLOAD_DIR, exist_ok=True)

    db.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(registro_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(report_bp)

    @app.route("/")
    def home():
        return redirect(url_for("registro.tela"))

    with app.app_context():
        db.create_all()
        semeia_inicial(app)
        _agenda_relatorio(app)

    return app


def _agenda_relatorio(app):
    """Agenda o envio mensal do relatório no dia configurado (default: dia 1)."""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        dia = int(Cfg.get("relatorio_dia", "1"))
        sched = BackgroundScheduler(daemon=True, timezone="America/Sao_Paulo")

        def job():
            with app.app_context():
                envia_relatorio_mensal()

        sched.add_job(job, "cron", day=dia, hour=6, minute=0, id="relatorio_mensal",
                      replace_existing=True)
        sched.start()
        app.config["SCHEDULER"] = sched
    except Exception as e:  # não derruba o app se o scheduler falhar
        app.logger.warning(f"Scheduler não iniciado: {e}")


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
