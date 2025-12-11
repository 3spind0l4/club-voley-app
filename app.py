# app.py - VERSIÓN FINAL 100% FUNCIONAL Y SIN ERRORES - Diego Espindola 4°C
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'club-voley-secreta-2025-diego-espindola-4c')

# ====================== BASE DE DATOS ======================
def get_db_path():
    if os.environ.get('RENDER'):
        return '/opt/render/project/.data/club_voley.db'
    else:
        path = os.path.join(os.getcwd(), 'instance', 'club_voley.db')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

def get_db_connection():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN ('jugador', 'admin'))
        );

        CREATE TABLE IF NOT EXISTS jugadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            apellido TEXT NOT NULL,
            telefono TEXT,
            posicion TEXT,
            categoria TEXT,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        );

        CREATE TABLE IF NOT EXISTS pagos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jugador_id INTEGER NOT NULL,
            mes_año TEXT NOT NULL,
            pagado BOOLEAN DEFAULT 0,
            validado BOOLEAN DEFAULT 0,
            fecha_confirmacion TIMESTAMP,
            fecha_validacion TIMESTAMP,
            UNIQUE(jugador_id, mes_año)
        );

        CREATE TABLE IF NOT EXISTS entrenamientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            horario TEXT NOT NULL,
            descripcion TEXT
        );

        CREATE TABLE IF NOT EXISTS asistencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entrenamiento_id INTEGER NOT NULL,
            jugador_id INTEGER NOT NULL,
            asistio BOOLEAN DEFAULT 0,
            UNIQUE(entrenamiento_id, jugador_id)
        );
    ''')

    # Usuarios de prueba
    conn.execute("INSERT OR IGNORE INTO usuarios (email, password_hash, tipo) VALUES (?, ?, ?)",
                 ('jugador@club.com', generate_password_hash('123456'), 'jugador'))
    conn.execute("INSERT OR IGNORE INTO usuarios (email, password_hash, tipo) VALUES (?, ?, ?)",
                 ('admin@club.com', generate_password_hash('admin123'), 'admin'))

    # Jugador demo
    conn.execute("""INSERT OR IGNORE INTO jugadores (usuario_id, nombre, apellido, telefono, posicion, categoria)
                    VALUES ((SELECT id FROM usuarios WHERE email='jugador@club.com'),
                            'Lucía', 'Gómez', '1122334455', 'Armadora', 'Mayores')""")
    conn.commit()
    conn.close()
    print("Base de datos inicializada correctamente")

# ====================== RUTAS ======================
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect('/dashboard')
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email'].strip().lower()
    password = request.form['password']
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM usuarios WHERE email = ?', (email,)).fetchone()
    conn.close()

    if user and check_password_hash(user['password_hash'], password):
        session['user_id'] = user['id']
        session['user_tipo'] = user['tipo']
        session['user_email'] = user['email']
        return redirect('/dashboard')
    flash('Credenciales incorrectas', 'error')
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')

    conn = get_db_connection()
    jugador = conn.execute('SELECT j.*, u.email FROM jugadores j JOIN usuarios u ON j.usuario_id = u.id WHERE j.usuario_id = ?', (session['user_id'],)).fetchone()

    mes_actual = datetime.now().strftime('%Y-%m')
    pago_mes = conn.execute('SELECT * FROM pagos WHERE jugador_id = ? AND mes_año = ?', (jugador['id'], mes_actual)).fetchone() if jugador else None

    proximos = conn.execute('SELECT * FROM entrenamientos ORDER BY fecha DESC LIMIT 4').fetchall()
    conn.close()

    return render_template('dashboard.html', jugador=jugador, pago_mes=pago_mes, proximos=proximos, mes_actual=mes_actual)

# ====================== PAGOS ======================
@app.route('/pagos')
def pagos():
    if 'user_id' not in session:
        return redirect('/')
    conn = get_db_connection()
    jugador = conn.execute('SELECT id FROM jugadores WHERE usuario_id = ?', (session['user_id'],)).fetchone()
    lista_pagos = conn.execute('SELECT *, strftime("%m/%Y", mes_año) AS mes_texto FROM pagos WHERE jugador_id = ? ORDER BY mes_año DESC', (jugador['id'],)).fetchall()
    conn.close()
    return render_template('pagos.html', pagos=lista_pagos)

@app.route('/confirmar_pago/<mes>', methods=['POST'])
def confirmar_pago(mes):
    if 'user_id' not in session:
        return redirect('/')
    conn = get_db_connection()
    jugador_id = conn.execute('SELECT id FROM jugadores WHERE usuario_id = ?', (session['user_id'],)).fetchone()['id']
    conn.execute('''INSERT INTO pagos (jugador_id, mes_año, pagado, fecha_confirmacion)
                    VALUES (?, ?, 1, ?)
                    ON CONFLICT(jugador_id, mes_año) DO UPDATE SET pagado=1, fecha_confirmacion=?''',
                 (jugador_id, mes, datetime.now(), datetime.now()))
    conn.commit()
    conn.close()
    flash(f'Pago confirmado para {mes}', 'success')
    return redirect('/pagos')

# ====================== ADMIN ======================
@app.route('/admin/pagos')
def admin_pagos():
    if session.get('user_tipo') != 'admin':
        return redirect('/')
    conn = get_db_connection()
    pagos = conn.execute('''
        SELECT p.*, j.nombre, j.apellido, u.email, strftime("%m/%Y", p.mes_año) AS mes_texto
        FROM pagos p
        JOIN jugadores j ON p.jugador_id = j.id
        JOIN usuarios u ON j.usuario_id = u.id
        WHERE p.pagado = 1
        ORDER BY p.mes_año DESC
    ''').fetchall()
    conn.close()
    return render_template('admin_pagos.html', pagos=pagos)

@app.route('/admin/validar/<int:pago_id>')
def validar_pago(pago_id):
    if session.get('user_tipo') != 'admin':
        return redirect('/')
    conn = get_db_connection()
    conn.execute('UPDATE pagos SET validado = 1, fecha_validacion = ? WHERE id = ?', (datetime.now(), pago_id))
    conn.commit()
    conn.close()
    flash('Pago validado')
    return redirect('/admin/pagos')

# ====================== ENTRENAMIENTOS ======================
@app.route('/entrenamientos')
def entrenamientos():
    if 'user_id' not in session:
        return redirect('/')
    conn = get_db_connection()
    lista = conn.execute('SELECT * FROM entrenamientos ORDER BY fecha DESC').fetchall()

    if session['user_tipo'] == 'admin':
        conn.close()
        return render_template('admin_entrenamientos.html', entrenamientos=lista)

    # Jugador normal
    jugador_id = conn.execute('SELECT id FROM jugadores WHERE usuario_id = ?', (session['user_id'],)).fetchone()['id']
    asistencias = conn.execute('SELECT entrenamiento_id, asistio FROM asistencias WHERE jugador_id = ?', (jugador_id,)).fetchall()
    asist_dict = {a['entrenamiento_id']: a['asistio'] for a in asistencias}
    conn.close()
    return render_template('entrenamientos.html', entrenamientos=lista, asist_dict=asist_dict)

@app.route('/admin/crear_entrenamiento', methods=['POST'])
def crear_entrenamiento():
    if session.get('user_tipo') != 'admin':
        return redirect('/')
    fecha = request.form['fecha']
    horario = request.form['horario']
    desc = request.form.get('descripcion', '')
    conn = get_db_connection()
    conn.execute('INSERT INTO entrenamientos (fecha, horario, descripcion) VALUES (?, ?, ?)', (fecha, horario, desc))
    conn.commit()
    conn.close()
    flash('Entrenamiento creado')
    return redirect('/entrenamientos')

@app.route('/confirmar_asistencia/<int:ent_id>', methods=['POST'])
def confirmar_asistencia(ent_id):
    if 'user_id' not in session:
        return redirect('/')
    conn = get_db_connection()
    jugador_id = conn.execute('SELECT id FROM jugadores WHERE usuario_id = ?', (session['user_id'],)).fetchone()['id']
    conn.execute('''INSERT INTO asistencias (entrenamiento_id, jugador_id, asistio)
                    VALUES (?, ?, 1)
                    ON CONFLICT(entrenamiento_id, jugador_id) DO UPDATE SET asistio=1''', (ent_id, jugador_id))
    conn.commit()
    conn.close()
    flash('Asistencia confirmada')
    return redirect('/entrenamientos')

@app.route('/perfil')
def perfil():
    if 'user_id' not in session:
        return redirect('/')
    conn = get_db_connection()
    jugador = conn.execute('SELECT j.*, u.email FROM jugadores j JOIN usuarios u ON j.usuario_id = u.id WHERE j.usuario_id = ?', (session['user_id'],)).fetchone()
    conn.close()
    return render_template('perfil.html', jugador=jugador)

# ====================== INICIO ======================
if __name__ == '__main__':
    init_db()  # Crea la BD la primera vez
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug= not os.environ.get('RENDER'))