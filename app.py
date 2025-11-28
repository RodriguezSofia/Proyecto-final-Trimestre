from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import psycopg2
from psycopg2.extras import RealDictCursor
import bcrypt
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'Dulce_manjar')


# -------------------------
# CONFIGURACIÓN DE LA BD
# -------------------------
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'database': os.environ.get('DB_NAME', 'heladeria'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', '123456'),
    'port': 5432
}

def conectar_bd():
    try:
        return psycopg2.connect(**DB_CONFIG)
    except psycopg2.Error as e:
        print(f"Error al conectar a la base de datos: {e}")
        return None


# -------------------------
# RUTA PRINCIPAL (INDEX)
# -------------------------
@app.route('/')
def home():
    return render_template('index.html')   # AHORA INICIA EN INDEX.HTML

# -------------------------
# RUTAS PARA NAVEGAR DESDE EL MENÚ DEL INDEX
# -------------------------

@app.route('/menu')
def menu():
    return render_template('menu.html')

@app.route('/sabores')
def sabores():
    return render_template('sabores.html')

@app.route('/acerca')
def acerca():
    return render_template('acerca_de_nosotros.html')

@app.route('/contacto')
def contacto():
    return render_template('contacto.html')
# -------------------------
# RUTAS PARA NAVEGAR EL ADMIN PANEL
# -------------------------
@app.route('/pedidos')
def pedidos():
    return render_template('pedidos.html')

@app.route('/productos')
def productos():
    return render_template('productos.html')

@app.route('/clientes')
def clientes():
    return render_template('clientes.html')

@app.route('/reportes')
def reportes():
    return render_template('reportes.html')

@app.route('/trabajadores')
def trabajadores():
    return render_template('trabajadores.html')

# -------------------------
# REGISTRO
# -------------------------
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'GET':
        return render_template('registro.html')
    
    datos = request.get_json()
    nombre = datos.get('nombre_completo', '').strip()
    correo = datos.get('correo', '').strip()
    contrasena = datos.get('contrasena', '').strip()
    confirmar_contrasena = datos.get('confirmar_contrasena', '').strip()

    if not nombre or not correo or not contrasena:
        return jsonify({'error': 'Todos los campos son obligatorios'}), 400

    if contrasena != confirmar_contrasena:
        return jsonify({'error': 'Las contraseñas no coinciden'}), 400

    password_hash = bcrypt.hashpw(contrasena.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    conexion = conectar_bd()
    if not conexion:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500

    try:
        cursor = conexion.cursor()

        cursor.execute('SELECT * FROM public."Usuarios" WHERE "correo_usuario" = %s;', (correo,))
        if cursor.fetchone():
            cursor.close()
            conexion.close()
            return jsonify({'error': 'El correo ya está registrado'}), 400

        cursor.execute("""
            INSERT INTO public."Usuarios"
            ("Nombre_completo_usuario", "correo_usuario", "password", "Id_tipo")
            VALUES (%s, %s, %s, %s)
            RETURNING "Id_usuario";
        """, (nombre, correo, password_hash, 3))

        nuevo_id = cursor.fetchone()[0]
        conexion.commit()
        cursor.close()
        conexion.close()

        return jsonify({'mensaje': 'Usuario registrado exitosamente', 'id_usuario': nuevo_id}), 201

    except Exception as e:
        print(f"Error al registrar usuario: {e}")
        if 'conexion' in locals():
            conexion.rollback()
            cursor.close()
            conexion.close()
        return jsonify({'error': 'Error interno del servidor'}), 500


# -------------------------
# LOGIN
# -------------------------
# -------------------------
# LOGIN
# -------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    datos = request.get_json()

    correo = datos.get("correo", "").strip()
    password = datos.get("password", "").strip()

    if not correo or not password:
        return jsonify({"error": "Todos los campos son obligatorios"}), 400

    conexion = conectar_bd()
    if not conexion:
        return jsonify({"error": "Error de conexión a la base de datos"}), 500

    try:
        cursor = conexion.cursor(cursor_factory=RealDictCursor)

        cursor.execute('SELECT * FROM public."Usuarios" WHERE "correo_usuario" = %s;', (correo,))
        usuario = cursor.fetchone()

        if not usuario:
            cursor.close()
            conexion.close()
            return jsonify({"error": "Correo no registrado"}), 404

        password_guardada = usuario["password"]

        if not bcrypt.checkpw(password.encode('utf-8'), password_guardada.encode('utf-8')):
            cursor.close()
            conexion.close()
            return jsonify({"error": "Contraseña incorrecta"}), 401

        session["usuario_id"] = usuario["Id_usuario"]

        cursor.close()
        conexion.close()

        # ------------------------------------
        # Login exitoso → verificar tipo
        # ------------------------------------
        if usuario["Id_tipo"] == 1:
            # Administrador
            return jsonify({"redirect": "/admin_panel"}), 200

        elif usuario["Id_tipo"] == 2:
            # Trabajador
            return jsonify({"redirect": "/admin_panel"}), 200

        else:
            # Cliente normal
            return jsonify({"redirect": "/"}), 200

    except Exception as e:
        print(f"Error en login: {e}")
        try:
            cursor.close()
            conexion.close()
        except:
            pass
        return jsonify({"error": "Error interno del servidor"}), 500

# -------------------------
# PANEL DE ADMINISTRADOR Y TRABAJADORES
# -------------------------
@app.route('/admin_panel')
def admin_panel():
    if "usuario_id" not in session:
        return redirect(url_for('login'))

    conexion = conectar_bd()
    if not conexion:
        return "Error al conectar a la BD", 500

    try:
        cursor = conexion.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT "Id_tipo" FROM public."Usuarios" WHERE "Id_usuario" = %s;', (session["usuario_id"],))
        usuario = cursor.fetchone()

        cursor.close()
        conexion.close()

        # Administrador
        if usuario["Id_tipo"] == 1:
            return render_template('admin_panel.html')

        # Trabajador
        if usuario["Id_tipo"] == 2:
            return render_template('panel_trabajadores.html')

        # Cliente → index normal
        return redirect(url_for('home'))

    except Exception as e:
        print(e)
        return "Error interno del servidor", 500


# -------------------------
# EJECUCIÓN DEL SERVIDOR
# -------------------------
if __name__ == '__main__':
    print("Iniciando servidor...")
    app.run(debug=True, host='0.0.0.0', port=5000)