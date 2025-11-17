from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'clave_secreta_del_club_voley_2024'

# Función para conectar a la BD
def get_db_connection():
    conn = sqlite3.connect('instance/club_voley.db')
    conn.row_factory = sqlite3.Row
    return conn

# Verificar y crear BD si no existe
def check_and_init_db():
    try:
        conn = get_db_connection()
        conn.execute("SELECT 1 FROM usuarios LIMIT 1")
        conn.close()
        print("✅ Base de datos verificada correctamente")
    except sqlite3.OperationalError:
        print("🔄 Base de datos no existe. Creando tablas...")
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
        conn.commit()
        print("✅ Usuarios de prueba creados")
    except Exception as e:
        print(f"⚠️ Error creando usuarios: {e}")
    
    conn.close()

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
        # CORRECCIÓN: Redirigir al dashboard
        return redirect('/dashboard')
    else:
        return "❌ Credenciales incorrectas. <a href='/'>Volver</a>"

# Ruta del dashboard
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')
    
    conn = get_db_connection()
    user = conn.execute(
        'SELECT * FROM usuarios WHERE id = ?', 
        (session['user_id'],)
    ).fetchone()
    conn.close()
    
    return render_template('dashboard.html', user=user)
# Ruta de inicio (nuevo dashboard)
@app.route('/inicio')
def inicio():
    if 'user_id' not in session:
        return redirect('/')
    
    conn = get_db_connection()
    user = conn.execute(
        'SELECT * FROM usuarios WHERE id = ?', 
        (session['user_id'],)
    ).fetchone()
    conn.close()
    
    return render_template('inicio.html')

# Ruta de pagos (página independiente)
@app.route('/pagos')
def pagos():
    if 'user_id' not in session:
        return redirect('/')
    
    conn = get_db_connection()
    user = conn.execute(
        'SELECT * FROM usuarios WHERE id = ?', 
        (session['user_id'],)
    ).fetchone()
    
    # Obtener pagos del jugador
    pagos = conn.execute(
        'SELECT * FROM pagos WHERE jugador_id = ? ORDER BY mes_año DESC',
        (session['user_id'],)
    ).fetchall()
    
    conn.close()
    
    return render_template('pagos.html', user=user, pagos=pagos)

# Ruta de calendario (placeholder)
@app.route('/calendario')
def calendario():
    if 'user_id' not in session:
        return redirect('/')
    
    return render_template('calendario.html')

# Ruta de perfil (placeholder)
@app.route('/perfil')
def perfil():
    if 'user_id' not in session:
        return redirect('/')
    
    conn = get_db_connection()
    user = conn.execute(
        'SELECT * FROM usuarios WHERE id = ?', 
        (session['user_id'],)
    ).fetchone()
    conn.close()
    
    return render_template('perfil.html', user=user)

# Ruta de configuración (placeholder)
@app.route('/configuracion')
def configuracion():
    if 'user_id' not in session:
        return redirect('/')
    
    return render_template('configuracion.html')

# Y CAMBIÁ la ruta /dashboard para que redirija a /inicio
@app.route('/dashboard')
def dashboard():
    return redirect('/inicio')

if __name__ == '__main__':
    # Crear carpeta instance si no existe
    if not os.path.exists('instance'):
        os.makedirs('instance')
    
    # Verificar y crear BD si es necesario
    check_and_init_db()
    
    print("🚀 Servidor iniciado correctamente")
    
    # PARA RENDER - CONFIGURACIÓN CLOUD
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)