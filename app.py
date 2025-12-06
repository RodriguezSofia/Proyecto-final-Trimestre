from flask import Flask, request, jsonify, render_template, redirect, url_for, session 
from flask_mail import Mail, Message #Se importa para el envio de correos
import psycopg2
from psycopg2.extras import RealDictCursor
import bcrypt #Se importa bcrypt para el hash o no visualizacion de las contraseñas del usuario
import os  #Se importa os para mejor manejo de las variables del entorno
import random # Se importa random para la generacion de  contraseñas temporales.         
import string #En conjunto con random, se usa para la generación de contraseñas temporales

# ======================================================
# CONFIGURACIÓN GENERAL
# ======================================================

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'Dulce_manjar')

# ======================================================
# CONFIGURACIÓN EMAIL
# ======================================================

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'diaznicolk@gmail.com'  #CORREO DE DONDE SE VAN A ENVIAR LA CONTRASEÑAS TEMPORALES 
app.config['MAIL_PASSWORD'] = 'jpzv vwrw xeit bcva'       # contraseña de aplicación
app.config['MAIL_DEFAULT_SENDER'] = 'diaznicolk@gmail.com'  #CORREO DE DONDE SE VAN A ENVIAR LA CONTRASEÑAS TEMPORALES

mail = Mail(app)

# ======================================================
# CONFIGURACIÓN BASE DE DATOS
# ======================================================

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

# ======================================================
# FUNCIÓN: GENERAR CONTRASEÑA TEMPORAL
# ======================================================

def generar_contrasena_temporal():
    caracteres = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(random.choice(caracteres) for _ in range(8))

# ======================================================
# RUTAS PRINCIPALES
# ======================================================

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/menu')
def menu():
    return render_template('menu.html')

@app.route('/sabores')
def sabores():
    return render_template('sabores.html')

@app.route('/acerca')
def acerca():
    return render_template('acerca_de_nosotros.html')

# ======================================================
# RUTA PARA GUARDAR CONTACTOS
# ======================================================

# ======================================================
# RUTA ÚNICA: /contacto (GET → muestra el formulario, POST → guarda)
# ======================================================
@app.route('/contacto', methods=['GET', 'POST'])
def contacto():
    # GET: mostrar la plantilla
    if request.method == 'GET':
        return render_template('contacto.html')

    # POST: recibir datos y guardar en la BD
    try:
        datos = request.get_json(silent=True) or request.form
        correo = datos.get('correo', '').strip()
        mensaje = datos.get('mensaje', '').strip()

        if not correo or not mensaje:
            return jsonify({'error': 'correo y mensaje son obligatorios'}), 400

        conexion = conectar_bd()
        if not conexion:
            return jsonify({'error': 'Error al conectar a la base de datos'}), 500

        cursor = conexion.cursor()

        
        sql = """
            INSERT INTO "Contacto" (correo, mensaje, creado)
            VALUES (%s, %s, NOW())
            RETURNING id;
        """
        cursor.execute(sql, (correo, mensaje))
        contacto_id = cursor.fetchone()[0]

        conexion.commit()
        cursor.close()
        conexion.close()

        return jsonify({'mensaje': 'Contacto guardado exitosamente', 'id': contacto_id}), 201

    except Exception as e:
        print(f"Error al guardar el contacto: {e}")
        return jsonify({'error': 'Error interno al guardar el contacto'}), 500

# ======================================================
# ADMIN PANEL
# ======================================================

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

@app.route('/panel_trabajadores')
def panel_trabajadores():
    return render_template('panel_trabajadores.html')

@app.route('/factura')
def factura():
    return render_template('factura.html')


# ======================================================
# RUTA PARA LISTAR CONTACTOS (ADMIN / API)
# ======================================================
@app.route('/ver_contactos', methods=['GET'])
def ver_contactos():
    try:
        conexion = conectar_bd()
        if not conexion:
            return jsonify({'error': 'Error al conectar a la base de datos'}), 500

        cursor = conexion.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT * FROM Contacto ORDER BY creado DESC;')
        contactos = cursor.fetchall()
        cursor.close()
        conexion.close()

        # Formatear fecha
        for c in contactos:
            if c.get('creado'):
                c['creado'] = c['creado'].strftime('%Y-%m-%d %H:%M:%S')

        return jsonify(contactos), 200

    except Exception as e:
        print(f"Error al obtener contactos: {e}")
        return jsonify({'error': 'Error interno al obtener contactos'}), 500


# ======================================================
# REGISTRO DE USUARIO
# ======================================================

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
        conexion.rollback()
        cursor.close()
        conexion.close()
        return jsonify({'error': 'Error interno del servidor'}), 500

# ======================================================
# LOGIN
# ======================================================

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
        session["usuario_nombre"] = usuario["Nombre_completo_usuario"]
        session["usuario_tipo"] = usuario["Id_tipo"]

        

        cursor.close()
        conexion.close()

        if usuario["Id_tipo"] in (1, 2):
            return jsonify({"redirect": "/admin_panel"}), 200

        return jsonify({"redirect": "/"}), 200

    except Exception as e:
        print(f"Error en login: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

# ======================================================
# CAMBIO DE CONTRASEÑA (USUARIO LOGUEADO)
# ======================================================

@app.route('/cambiar_password', methods=['POST'])
def cambiar_password():
    if "usuario_id" not in session:
        return jsonify({'error': 'Debes iniciar sesión'}), 401

    datos = request.get_json()
    actual = datos.get("actual", "").strip()
    nueva = datos.get("nueva", "").strip()

    if not actual or not nueva:
        return jsonify({'error': 'Todos los campos son obligatorios'}), 400

    conexion = conectar_bd()
    cursor = conexion.cursor(cursor_factory=RealDictCursor)

    cursor.execute('SELECT "password" FROM public."Usuarios" WHERE "Id_usuario" = %s;',
                (session["usuario_id"],))
    usuario = cursor.fetchone()

    if not bcrypt.checkpw(actual.encode('utf-8'), usuario["password"].encode('utf-8')):
        return jsonify({'error': 'La contraseña actual es incorrecta'}), 400

    nueva_hash = bcrypt.hashpw(nueva.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    cursor.execute('UPDATE public."Usuarios" SET "password"=%s WHERE "Id_usuario"=%s;',
                (nueva_hash, session["usuario_id"]))

    conexion.commit()
    cursor.close()
    conexion.close()

    return jsonify({'mensaje': 'Contraseña actualizada correctamente'})

# ======================================================
# ADMIN PANEL (VALIDACIÓN DE ROL)
# ======================================================

@app.route('/admin_panel')
def admin_panel():
    if "usuario_id" not in session:
        return redirect(url_for('login'))

    conexion = conectar_bd()
    if not conexion:
        return "Error al conectar a la BD", 500

    try:
        cursor = conexion.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT "Id_tipo" FROM public."Usuarios" WHERE "Id_usuario" = %s;',
                    (session["usuario_id"],))
        usuario = cursor.fetchone()

        cursor.close()
        conexion.close()

        if usuario["Id_tipo"] == 1:
            return render_template('admin_panel.html')

        if usuario["Id_tipo"] == 2:
            return render_template('panel_trabajadores.html')

        return redirect(url_for('home'))

    except Exception as e:
        print(f"Error en admin_panel: {e}")
        return "Error interno", 500

# ======================================================
# RECUPERACIÓN DE CONTRASEÑA
# ======================================================

@app.route('/recuperacion', methods=['GET', 'POST'])
def recuperacion():
    if request.method == 'GET':
        return render_template('recuperacion.html')

    datos = request.get_json()
    correo = datos.get('correo', '').strip()

    if not correo:
        return jsonify({'error': 'El correo es obligatorio'}), 400

    conexion = conectar_bd()
    if not conexion:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500

    try:
        cursor = conexion.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT "Id_usuario", "Nombre_completo_usuario", "correo_usuario"
            FROM public."Usuarios"
            WHERE "correo_usuario" = %s;
        """, (correo,))

        usuario = cursor.fetchone()

        if not usuario:
            cursor.close()
            conexion.close()
            return jsonify({'error': 'El correo no está registrado'}), 404

        # generar contraseña temporal
        contrasena_temporal = generar_contrasena_temporal()

        password_hash = bcrypt.hashpw(contrasena_temporal.encode('utf-8'),
                                    bcrypt.gensalt()).decode('utf-8')

        cursor.execute("""
            UPDATE public."Usuarios"
            SET "password" = %s
            WHERE "correo_usuario" = %s;
        """, (password_hash, correo))

        conexion.commit()

        # enviar correo
        msg = Message('Contraseña temporal - Heladería Annia', recipients=[correo])
        msg.html = f"""
        <html>
            <body style="font-family: Arial; padding: 20px; background-color: #f5f5f5;">
                <div style="max-width: 600px; background:white; padding:30px; border-radius:10px;">
                    <h2 style="color:#FF69B4; text-align:center;">🍦 Heladería Annia</h2>
                    <p>Hola {usuario['Nombre_completo_usuario']},</p>
                    <p>Tu contraseña temporal es:</p>

                    <div style="background:#fff3cd; padding:18px; border-radius:5px; text-align:center;">
                        <strong style="font-size:22px;">{contrasena_temporal}</strong>
                    </div>

                    <br>
                    <a href="http://localhost:5000/login"
                       style="background:#FF69B4; padding:12px 35px; color:white; 
                              text-decoration:none; border-radius:20px; font-weight:bold;">
                       Iniciar Sesión
                    </a>
                </div>
            </body>
        </html>
        """

        mail.send(msg)

        cursor.close()
        conexion.close()

        return jsonify({'mensaje': 'Contraseña temporal enviada a tu correo'}), 200

    except Exception as e:
        print(f"Error en recuperación: {e}")
        conexion.rollback()
        cursor.close()
        conexion.close()
        return jsonify({'error': 'Error interno del servidor'}), 500
    
#------------CERRAR SESION--------------------
# ======================================================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


# ======================================================
# EJECUCIÓN
# ======================================================

if __name__ == '__main__':
    app.run(debug=True)
