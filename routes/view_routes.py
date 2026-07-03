from flask import Blueprint, render_template

view_bp = Blueprint("views", __name__)


@view_bp.route("/")
@view_bp.route("/login")
def login_page():
    return render_template("login.html")


@view_bp.route("/register")
def register_page():
    return render_template("register.html")


@view_bp.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")


@view_bp.route("/explorer")
def explorer_page():
    return render_template("public_explorer.html")


@view_bp.route("/shared-with-me")
def shared_page():
    return render_template("shared_with_me.html")