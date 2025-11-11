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
    except:
        pass
    
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
        return f'''
        <h1>¡Bienvenido {user['email']}!</h1>
        <p>Tipo de usuario: <strong>{user['tipo']}</strong></p>
        <a href="/">Volver al Login</a>
        '''
    else:
        return "❌ Credenciales incorrectas. <a href='/'>Volver</a>"

if __name__ == '__main__':
    # Crear carpeta instance si no existe
    if not os.path.exists('instance'):
        os.makedirs('instance')
    
    # Inicializar base de datos
    init_db()
    
    # PARA RENDER - CONFIGURACIÓN CLOUD
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)