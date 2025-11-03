import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, abort, g, jsonify
from dotenv import load_dotenv

load_dotenv()

ADMIN_KEY = os.getenv("ADMIN_KEY", "cambiame-por-una-clave-secreta")
DB_PATH = os.getenv("DB_PATH", "rsvps.db")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "cambiame-para-produccion")

# ---------- DB helpers ----------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS rsvps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            confirma INTEGER NOT NULL,
            menu TEXT,
            mensaje TEXT,
            created_at TEXT NOT NULL
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS invitados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL
        )
    """)
    db.commit()

@app.before_request
def ensure_db():
    init_db()

# ---------- Rutas ----------
@app.get("/")
def rsvp_form():
    return render_template("rsvp.html")

@app.post("/enviar")
def enviar_rsvp():
    try:
        nombre = (request.form.get("nombre") or "").strip()
        confirma_val = request.form.get("confirma")
        menu = (request.form.get("menu") or request.form.get("restricciones") or "").strip().lower()
        mensaje = (request.form.get("mensaje") or "").strip()

        errors = []
        if not nombre:
            errors.append("El nombre es obligatorio.")
        if confirma_val not in ("si", "no"):
            errors.append("Indicá si asistís o no.")
        if confirma_val == "si" and menu not in ("standard", "vegano"):
            errors.append("Elegí un menú: Standard o Vegano.")

        # Validar que el nombre exista en 'invitados'
        db = get_db()
        row_inv = db.execute("SELECT 1 FROM invitados WHERE nombre = ?", (nombre,)).fetchone()
        if not row_inv:
            errors.append("El nombre debe coincidir con un invitado cargado.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return redirect(url_for("rsvp_form"))

        confirma = 1 if confirma_val == "si" else 0

        db.execute("""
            INSERT INTO rsvps (nombre, confirma, menu, mensaje, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (nombre, confirma, menu if confirma == 1 else None, mensaje or None,
              datetime.now().isoformat(timespec="seconds")))
        db.commit()

        return redirect(url_for("gracias"), code=303)

    except Exception as ex:
        print("ERROR en /enviar:", ex)
        flash("Ocurrió un error guardando tu confirmación. Probá de nuevo.", "danger")
        return redirect(url_for("rsvp_form"))

@app.get("/gracias")
def gracias():
    return render_template("gracias.html")

@app.get("/admin")
def admin():
    key = request.args.get("key", "")
    if key != ADMIN_KEY:
        abort(401)

    db = get_db()
    rsvps = db.execute("""
        SELECT id, nombre, confirma, menu, mensaje, created_at
        FROM rsvps
        ORDER BY created_at DESC
    """).fetchall()

    invitados = db.execute("""
        SELECT nombre FROM invitados ORDER BY nombre ASC
    """).fetchall()

    total_si = sum(1 for r in rsvps if r["confirma"] == 1)
    total_no = sum(1 for r in rsvps if r["confirma"] == 0)
    total_standard = sum(1 for r in rsvps if r["confirma"] == 1 and (r["menu"] or "").lower() == "standard")
    total_vegano = sum(1 for r in rsvps if r["confirma"] == 1 and (r["menu"] or "").lower() == "vegano")

    return render_template(
        "admin.html",
        rsvps=rsvps,
        invitados=[x["nombre"] for x in invitados],
        cant_invitados=len(invitados),
        total_si=total_si,
        total_no=total_no,
        total_standard=total_standard,
        total_vegano=total_vegano
    )

@app.post("/admin/cargar_invitados")
def admin_cargar_invitados():
    key = request.args.get("key", "")
    if key != ADMIN_KEY:
        abort(401)

    lista = (request.form.get("lista") or "").strip()
    if not lista:
        return redirect(url_for("admin", key=key))

    nombres = []
    for linea in lista.splitlines():
        for nombre in linea.split(","):
            nombre = nombre.strip()
            if nombre:
                nombres.append(nombre)

    db = get_db()
    for n in nombres:
        try:
            db.execute("INSERT OR IGNORE INTO invitados(nombre) VALUES (?)", (n,))
        except:
            pass
    db.commit()

    return redirect(url_for("admin", key=key))

# --- API para autocompletar ---
@app.get("/api/invitados")
def api_invitados():
    """Devuelve invitados SIN confirmar para autocompletar."""
    q = (request.args.get("q") or "").strip()
    db = get_db()

    # Invitados que todavía no registraron RSVP
    base_query = """
        SELECT i.nombre 
        FROM invitados i
        LEFT JOIN rsvps r ON r.nombre = i.nombre
        WHERE r.nombre IS NULL
    """

    params = []
    if q:
        base_query += " AND i.nombre LIKE ?"
        params.append(f"%{q}%")

    base_query += " ORDER BY i.nombre LIMIT 50"

    filas = db.execute(base_query, params).fetchall()

    return jsonify({"ok": True, "items": [f["nombre"] for f in filas]})

if __name__ == "__main__":
    app.run(debug=True)
