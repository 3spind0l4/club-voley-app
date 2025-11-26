from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'clave_secreta_del_club_voley_2024')

# Función para conectar a la BD - CORREGIDA
def get_db_connection():
    # Si estamos en Render, usar carpeta persistente
    if os.environ.get('RENDER') == 'true':
        db_path = '/opt/render/project/.data/club_voley.db'
    else:
        # Desarrollo local
        db_path = os.path.join(os.getcwd(), 'instance', 'club_voley.db')
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# Verificar y crear BD si no existe - CORREGIDA
def check_and_init_db():
    try:
        conn = get_db_connection()
        # Verificar si la tabla usuarios existe
        conn.execute("SELECT 1 FROM usuarios LIMIT 1")
        conn.close()
        print("✅ Base de datos verificada correctamente")
    except sqlite3.OperationalError as e:
        print(f"🔄 Base de datos no existe. Creando tablas... Error: {e}")
        init_db()

# Crear tablas si no existen
def init_db():
    conn = get_db_connection()
    
    # Tabla de usuarios
    conn.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            tipo TEXT NOT NULL,
            codigo_invitacion TEXT,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabla de jugadores
    conn.execute('''
        CREATE TABLE IF NOT EXISTS jugadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            nombre TEXT NOT NULL,
            apellido TEXT NOT NULL,
            telefono TEXT,
            posicion TEXT,
            categoria TEXT,
            foto_url TEXT,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    ''')
    
    # Tabla de pagos
    conn.execute('''
        CREATE TABLE IF NOT EXISTS pagos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jugador_id INTEGER,
            mes_año TEXT NOT NULL,
            monto REAL NOT NULL,
            fecha_pago DATE,
            estado TEXT NOT NULL,
            metodo_pago TEXT,
            comprobante_url TEXT,
            estado_confirmacion TEXT DEFAULT 'pendiente',
            confirmado_por INTEGER,
            fecha_confirmacion TIMESTAMP,
            validado_por INTEGER,
            fecha_validacion TIMESTAMP,
            FOREIGN KEY (jugador_id) REFERENCES jugadores (id)
        )
    ''')
    
    # Insertar usuario de prueba
    try:
        conn.execute(
            "INSERT OR IGNORE INTO usuarios (email, password, tipo) VALUES (?, ?, ?)",
            ('jugador@club.com', '123456', 'jugador')
        )
        conn.execute(
            "INSERT OR IGNORE INTO usuarios (email, password, tipo, codigo_invitacion) VALUES (?, ?, ?, ?)",
            ('admin@club.com', 'admin123', 'admin', 'CLUB2024')
        )
        
        # Obtener el ID del usuario jugador para insertar en jugadores
        usuario_jugador = conn.execute(
            "SELECT id FROM usuarios WHERE email = ?", 
            ('jugador@club.com',)
        ).fetchone()
        
        if usuario_jugador:
            conn.execute(
                "INSERT OR IGNORE INTO jugadores (usuario_id, nombre, apellido, telefono, posicion, categoria) VALUES (?, ?, ?, ?, ?, ?)",
                (usuario_jugador['id'], 'Jugador', 'Demo', '123456789', 'Armador', 'Mayores')
            )
        
        conn.commit()
        print("✅ Usuarios de prueba creados")
    except Exception as e:
        print(f"⚠️ Error creando usuarios: {e}")
        conn.rollback()
    
    conn.close()

# Ruta para verificar el estado de la BD
@app.route('/debug/db')
def debug_db():
    try:
        conn = get_db_connection()
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        conn.close()
        return f"Tablas en la BD: {[table['name'] for table in tables]}"
    except Exception as e:
        return f"Error: {e}"

# Ruta principal - Login
@app.route('/')
def home():
    return render_template('login.html')

# Procesar login
@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    
    conn = get_db_connection()
    user = conn.execute(
        'SELECT * FROM usuarios WHERE email = ? AND password = ?', 
        (email, password)
    ).fetchone()
    conn.close()
    
    if user:
        session['user_id'] = user['id']
        session['user_type'] = user['tipo']
        session['user_email'] = user['email']
        return redirect('/dashboard')
    else:
        return "❌ Credenciales incorrectas. <a href='/'>Volver</a>"

# Ruta del DASHBOARD
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')
    
    conn = get_db_connection()
    user = conn.execute(
        'SELECT * FROM usuarios WHERE id = ?', 
        (session['user_id'],)
    ).fetchone()
    
    # Obtener jugador asociado al usuario
    jugador = conn.execute(
        'SELECT * FROM jugadores WHERE usuario_id = ?',
        (session['user_id'],)
    ).fetchone()
    
    # Obtener pagos del jugador
    pagos = conn.execute(
        'SELECT * FROM pagos WHERE jugador_id = ? ORDER BY mes_año DESC',
        (session['user_id'],)
    ).fetchall()
    
    conn.close()
    
    return render_template('dashboard.html', user=user, jugador=jugador, pagos=pagos)

# Ruta para confirmar pago
@app.route('/confirmar_pago', methods=['POST'])
def confirmar_pago():
    if 'user_id' not in session:
        return redirect('/')
    
    mes_año = request.form['mes_año']
    metodo_pago = request.form['metodo_pago']
    
    conn = get_db_connection()
    
    # Verificar si ya existe un pago para este mes
    pago_existente = conn.execute(
        'SELECT * FROM pagos WHERE jugador_id = ? AND mes_año = ?',
        (session['user_id'], mes_año)
    ).fetchone()
    
    if pago_existente:
        # Actualizar pago existente
        conn.execute(
            '''UPDATE pagos SET 
               metodo_pago = ?, estado_confirmacion = 'confirmado',
               confirmado_por = ?, fecha_confirmacion = ?
               WHERE id = ?''',
            (metodo_pago, session['user_id'], datetime.now(), pago_existente['id'])
        )
    else:
        # Crear nuevo pago
        conn.execute(
            '''INSERT INTO pagos 
               (jugador_id, mes_año, monto, estado, metodo_pago, estado_confirmacion, confirmado_por, fecha_confirmacion) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (session['user_id'], mes_año, 5000, 'pendiente', metodo_pago, 'confirmado', session['user_id'], datetime.now())
        )
    
    conn.commit()
    conn.close()
    
    return redirect('/dashboard')

# Ruta para ver todos los pagos (admin)
@app.route('/admin/pagos')
def admin_pagos():
    if 'user_id' not in session or session['user_type'] != 'admin':
        return redirect('/')
    
    conn = get_db_connection()
    pagos = conn.execute('''
        SELECT p.*, u.email, j.nombre, j.apellido 
        FROM pagos p 
        JOIN usuarios u ON p.jugador_id = u.id 
        JOIN jugadores j ON p.jugador_id = j.usuario_id 
        ORDER BY p.mes_año DESC, p.estado_confirmacion
    ''').fetchall()
    conn.close()
    
    return render_template('admin_pagos.html', pagos=pagos)

# Ruta para validar pago (admin)
@app.route('/validar_pago/<int:pago_id>')
def validar_pago(pago_id):
    if 'user_id' not in session or session['user_type'] != 'admin':
        return redirect('/')
    
    conn = get_db_connection()
    conn.execute(
        '''UPDATE pagos SET 
           estado_confirmacion = 'validado',
           validado_por = ?, fecha_validacion = ?
           WHERE id = ?''',
        (session['user_id'], datetime.now(), pago_id)
    )
    conn.commit()
    conn.close()
    
    return redirect('/admin/pagos')

# Ruta para rechazar pago (admin)
@app.route('/rechazar_pago/<int:pago_id>')
def rechazar_pago(pago_id):
    if 'user_id' not in session or session['user_type'] != 'admin':
        return redirect('/')
    
    conn = get_db_connection()
    conn.execute(
        '''UPDATE pagos SET 
           estado_confirmacion = 'rechazado',
           validado_por = ?, fecha_validacion = ?
           WHERE id = ?''',
        (session['user_id'], datetime.now(), pago_id)
    )
    conn.commit()
    conn.close()
    
    return redirect('/admin/pagos')

# Ruta de perfil
@app.route('/perfil')
def perfil():
    if 'user_id' not in session:
        return redirect('/')
    
    conn = get_db_connection()
    user = conn.execute(
        'SELECT * FROM usuarios WHERE id = ?', 
        (session['user_id'],)
    ).fetchone()
    
    jugador = conn.execute(
        'SELECT * FROM jugadores WHERE usuario_id = ?',
        (session['user_id'],)
    ).fetchone()
    
    conn.close()
    
    return render_template('perfil.html', user=user, jugador=jugador)

# Ruta de partidos
@app.route('/partidos')
def partidos():
    if 'user_id' not in session:
        return redirect('/')
    
    return render_template('partidos.html')

# Ruta de pagos
@app.route('/pagos')
def pagos():
    if 'user_id' not in session:
        return redirect('/')
    
    conn = get_db_connection()
    pagos_list = conn.execute(
        'SELECT * FROM pagos WHERE jugador_id = ? ORDER BY mes_año DESC',
        (session['user_id'],)
    ).fetchall()
    
    conn.close()
    
    return render_template('pagos.html', pagos=pagos_list)

# Ruta de logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    # Verificar y crear BD si es necesario
    check_and_init_db()
    
    print("🚀 Servidor iniciado correctamente")
    print("👤 Usuario prueba: jugador@club.com / 123456")
    print("🔧 Admin prueba: admin@club.com / admin123")
    print("🔍 Ruta debug BD: /debug/db")
    
    # PARA RENDER - CONFIGURACIÓN CLOUD
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)