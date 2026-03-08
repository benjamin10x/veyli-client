from flask import Blueprint, render_template

main = Blueprint("main", __name__)

@main.route("/")
def index():
    return render_template("index.html")

@main.route("/recuperar")
def recuperar():
    return render_template("recuperar.html")

@main.route("/registro")
def registro():
    return render_template("registro.html")

@main.route("/inicio")
def inicio():
    return render_template("inicio.html")

@main.route("/envios")
def envios():
    return render_template("envios.html")

@main.route("/rastrear")
def rastrear():
    return render_template("rastrear.html")

@main.route("/historial")
def historial():
    return render_template("historial.html")