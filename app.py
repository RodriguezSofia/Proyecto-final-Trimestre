from flask import Flask, request, jsonify, render_template, redirect, url_for, session 
from flask_mail import Mail, Message #Se importa para el envio de correos
import psycopg2
from psycopg2.extras import RealDictCursor
import bcrypt #Se importa bcrypt para el hash o no visualizacion de las contraseñas del usuario
import os  #Se importa os para mejor manejo de las variables del entorno
import random # Se importa random para la generacion de  contraseñas temporales.         
import string #En conjunto con random, se usa para la generación de contraseñas temporales
from werkzeug.utils import secure_filename # Se importa para manejar la seguridad de los nombres de archivos subidos.

# ======================================================
# CONFIGURACIÓN GENERAL
# ======================================================

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'Dulce_manjar')
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'img') # Carpeta para guardar las imágenes subidas.
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'} #Modolo seguro para permitir solo ciertos tipos de archivos (imágenes) al subir.

def allowed_file(filename): # Función para verificar si el archivo tiene una extensión permitida.
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS # Verifica que el nombre del archivo contenga un punto y que la extensión (lo que viene después del último punto) esté en el conjunto de extensiones permitidas.

# ======================================================
# CONFIGURACIÓN EMAIL
# ======================================================

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'diaznicolk@gmail.com'  #CORREO DE DONDE SE VAN A ENVIAR LA CONTRASEÑAS TEMPORALES 
app.config['MAIL_PASSWORD'] = 'jpzv vwrw xeit bcva'       # contraseña de aplicación
app.config['MAIL_DEFAULT_SENDER'] = 'diaznicolk@gmail.com'  #CORREO DE DONDE SE VAN A ENVIAR LA CONTRASEÑAS TEMPORALES

mail = Mail(app) # Inicializa la extensión Flask-Mail con la configuración de la aplicación.

# ======================================================
# CONFIGURACIÓN BASE DE DATOS
# ======================================================

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'database': os.environ.get('DB_NAME', 'Heladeria'),
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
    caracteres = string.ascii_letters + string.digits + "!@#$%" # Define un conjunto de caracteres posibles (letras, dígitos y símbolos).
    return ''.join(random.choice(caracteres) for _ in range(8)) # Genera una cadena de 8 caracteres elegidos al azar.

# ======================================================
# RUTA PARA GENERAR MENÚ (GET)
# ======================================================

@app.route('/menu')
def menu():
    conexion = conectar_bd()
    if not conexion:
        return "Error al conectar a la base de datos", 500

    try:
        cursor = conexion.cursor(cursor_factory=RealDictCursor)

        #Recorrer productos, sabores y toppings para mostrar en el menú
        cursor.execute("""
            SELECT "Id_producto", "Nombre_producto", "Precio_producto", 
                   "Imagen", "Descripción", "Numero_bolas"
            FROM public."Productos";
        """)
        productos = cursor.fetchall()

        cursor.execute("""
            SELECT "Id_sabor", "Nombre_sabor"
            FROM public."Sabor";
        """)
        sabores = cursor.fetchall()

        cursor.execute("""
            SELECT "Id_toppings", "Nombre_toppings"
            FROM public."Toppings";
        """)
        toppings = cursor.fetchall()
        cursor.close()
        conexion.close()

        return render_template( # Renderiza la plantilla 'menu.html' y le pasa los datos de productos, sabores y toppings para que puedan ser mostrados en la página.
            'menu.html',
            productos=productos,
            sabores=sabores,
            toppings=toppings  
        )
    except Exception as e:
        print("Error cargando menú:", e)
        return "Error interno cargando menú", 500

# ======================================================
# RUTA PARA GENERAR FACTURA 
# ======================================================
@app.route('/confirmar_pedido', methods=['GET', 'POST'])
def confirmar_pedido():
    id_usuario = session.get("usuario_id")
    if not id_usuario:
        return redirect(url_for('login'))

    if request.method == 'POST': # Recibe los datos del formulario para crear la factura y el detalle de la factura.
        nombre_destinatario = request.form.get("nombre_destinatario")
        direccion = request.form.get("direccion")
        id_metodo = request.form.get("metodo_pago")

        if not nombre_destinatario or not direccion: # Verifica que se hayan proporcionado el nombre del destinatario y la dirección de envío. Si falta alguno de estos datos, devuelve un error 400 indicando que los datos de envío son incompletos.
            return "Datos de envío incompletos", 400

        # Construir el carrito a partir de los datos del formulario. Se espera que los datos del carrito se envíen con un formato específico, donde cada producto tiene un índice (carrito[0], carrito[1], etc.) y dentro de cada producto se incluyen los ids de los sabores seleccionados y el precio.
        carrito = []
        index = 0
        while True: 
            prefix = f"carrito[{index}]"
            id_producto = request.form.get(f"{prefix}[id_producto]")
            if not id_producto:
                break

            # Obtener los ids de los sabores
            sabores_ids = request.form.getlist(f"{prefix}[sabores]")
            if not sabores_ids:
                return f"Producto {id_producto} sin sabores seleccionados", 400

            # Convertir a enteros
            sabores_ids = [int(s) for s in sabores_ids]

            precio = float(request.form.get(f"{prefix}[precio]"))
            carrito.append({
                "id_producto": int(id_producto),
                "sabores": sabores_ids,
                "precio": precio
            })
            index += 1

        if not carrito:
            return "Carrito vacío", 400

        try:
            conexion = conectar_bd()
            cursor = conexion.cursor()

            # Insertar factura
            cursor.execute("""
                INSERT INTO public."Factura"(
                    "Fecha", "Id_metodo", "Id_usuario",
                    "Nombre_destinatario", "Direccion_envio"
                )
                VALUES (NOW(), %s, %s, %s, %s)
                RETURNING "Id_factura";
            """, (id_metodo, id_usuario, nombre_destinatario, direccion))
            id_factura = cursor.fetchone()[0]

            # Insertar detalle por cada sabor
            for item in carrito:
                for id_sabor in item["sabores"]:
                    cursor.execute("""
                        SELECT "Id_product_sabor"
                        FROM public."Producto_Sabor"
                        WHERE "Id_producto" = %s AND "Id_sabor" = %s;
                    """, (item["id_producto"], id_sabor))
                    result = cursor.fetchone()
                    if result:
                        id_product_sabor = result[0]
                        cursor.execute("""
                            INSERT INTO public."Detalle_factura"(
                            "Id_factura", "Id_product_sabor", "Id_toppings", "Total"
                            ) VALUES (%s, %s, %s, %s);
                        """, (id_factura, id_product_sabor, 4, item["precio"]))


            conexion.commit()
            cursor.close()
            conexion.close()

            return render_template("pedido_realizado.html", id_factura=id_factura)

        except Exception as e:
            print("Error guardando factura:", e)
            return "Error interno", 500

    # GET → mostrar formulario
    conexion = conectar_bd()
    cursor = conexion.cursor(cursor_factory=RealDictCursor)
    cursor.execute('SELECT "Id_metodo", "Nombre_pago" FROM public."Metodos_pago";')
    metodos_pago = cursor.fetchall()
    cursor.close()
    conexion.close()
    return render_template("confirmar_pedido.html", metodos_pago=metodos_pago)

@app.route('/factura')
def factura():
    return render_template('factura.html')

# ======================================================
# RUTAS PRINCIPALES
# ======================================================

@app.route('/')
def home(): #coneccion a la base de datos para obtener los sabores y toppings
    try:
        conexion = conectar_bd()
        cursor = conexion.cursor(cursor_factory=RealDictCursor)

        #Sabores
        cursor.execute("""
            SELECT "Id_sabor", "Nombre_sabor","Descripción", "Imagen"
            FROM public."Sabor";
        """)
        sabores = cursor.fetchall()

        #Toppings, se excluye "Sin topping" para mejor presentacion
        cursor.execute("""
            SELECT "Id_toppings", "Nombre_toppings", "Imagen"
            FROM public."Toppings"
            WHERE "Nombre_toppings" != 'Sin topping';
        """)
        toppings = cursor.fetchall()

        cursor.close()
        conexion.close()

        return render_template(
            'index.html',
            sabores=sabores,
            toppings=toppings
        )

    except Exception as e:
        print("Error cargando datos del home:", e)
        return "Error interno cargando la página principal"


@app.route('/redes')
def redes():
    return render_template('redes.html')

@app.route('/acerca')
def acerca():
    return render_template('acerca_de_nosotros.html')

# ======================================================
# RUTA PARA GUARDAR CONTACTOS
# ======================================================

@app.route('/contacto', methods=['GET', 'POST'])
def contacto():
    # GET: mostrar la plantilla
    if request.method == 'GET': # Verifica si la solicitud es GET (para mostrar el formulario).
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

@app.route('/admin/pedidos', methods=['GET', 'POST'])
def admin_pedidos():
    conexion = conectar_bd()
    if not conexion:
        return "Error al conectar a la base de datos", 500

    detalle_pedido = []  # 👈 inicializar vacío

    try:
        cursor = conexion.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT 
                f."Id_factura",
                f."Fecha",
                f."Nombre_destinatario",
                SUM(d."Total") AS total
            FROM public."Factura" f
            JOIN public."Detalle_factura" d 
                ON f."Id_factura" = d."Id_factura"
            GROUP BY 
                f."Id_factura",
                f."Fecha",
                f."Nombre_destinatario"
            ORDER BY f."Id_factura" DESC;
        """)

        pedidos = cursor.fetchall()

        # Manejar POST para mostrar detalle
        if request.method == "POST":
            id_factura = request.form.get("id_factura")
            cursor.execute("""
                SELECT p."Nombre_producto", s."Nombre_sabor", df."Total", df."Id_factura"
                FROM public."Detalle_factura" df
                JOIN public."Producto_Sabor" ps ON df."Id_product_sabor" = ps."Id_product_sabor"
                JOIN public."Productos" p ON ps."Id_producto" = p."Id_producto"
                JOIN public."Sabor" s ON ps."Id_sabor" = s."Id_sabor"
                WHERE df."Id_factura" = %s;
            """, (id_factura,))
            detalle_pedido = cursor.fetchall()  # 👈 aquí ya es lista

        cursor.close()
        conexion.close()

        return render_template('admin/pedidos.html', pedidos=pedidos, detalle_pedido=detalle_pedido)

    except Exception as e:
        print("Error cargando pedidos:", e)
        return "Error interno", 500

@app.route('/admin/productos')
def admin_productos():
    if "usuario_id" not in session or session.get("usuario_tipo") != 1:
        return redirect(url_for('login'))

    conexion = conectar_bd()
    cursor = conexion.cursor(cursor_factory=RealDictCursor)

    cursor.execute('SELECT * FROM public."Productos" ORDER BY "Id_producto";')
    productos = cursor.fetchall()

    cursor.execute('SELECT * FROM public."Sabor" ORDER BY "Id_sabor";')
    sabores = cursor.fetchall()

    cursor.execute("""
        SELECT * FROM public."Toppings"
        WHERE "Nombre_toppings" != 'Sin topping'
        ORDER BY "Id_toppings";
    """)
    toppings = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template(
        'admin/productos.html',
        productos=productos,
        sabores=sabores,
        toppings=toppings
    )

@app.route('/crear_producto', methods=['POST'])
def crear_producto():
    if "usuario_id" not in session or session.get("usuario_tipo") != 1:
        return redirect(url_for('login'))

    nombre = request.form.get('nombre')
    precio = request.form.get('precio')
    descripcion = request.form.get('descripcion')
    numero_bolas = request.form.get('numero_bolas')

    imagen = request.files.get('imagen')
    nombre_imagen = None

    if imagen and imagen.filename != '' and allowed_file(imagen.filename):
        nombre_imagen = secure_filename(imagen.filename)
        ruta = os.path.join('static', 'img', nombre_imagen)
        imagen.save(ruta)

    try:
        conexion = conectar_bd()
        cursor = conexion.cursor()

        cursor.execute("""
            INSERT INTO public."Productos"
            ("Nombre_producto", "Precio_producto", "Imagen", "Descripción", "Numero_bolas")
            VALUES (%s, %s, %s, %s, %s);
        """, (nombre, precio, nombre_imagen, descripcion, numero_bolas))

        conexion.commit()
        cursor.close()
        conexion.close()

        return redirect(url_for('admin_productos'))

    except Exception as e:
        print("Error creando producto:", e)
        return "Error al crear producto", 500

@app.route('/crear_sabor', methods=['POST'])
def crear_sabor():
    if "usuario_id" not in session or session.get("usuario_tipo") != 1:
        return redirect(url_for('login'))

    nombre = request.form.get('nombre')
    descripcion = request.form.get('descripcion')

    imagen = request.files.get('imagen')
    nombre_imagen = None

    if imagen and imagen.filename != '' and allowed_file(imagen.filename):
        nombre_imagen = secure_filename(imagen.filename)
        ruta = os.path.join('static', 'img', nombre_imagen)
        imagen.save(ruta)

    try:
        conexion = conectar_bd()
        cursor = conexion.cursor()

        cursor.execute("""
            INSERT INTO public."Sabor"
            ("Nombre_sabor", "Descripción", "Imagen")
            VALUES (%s, %s, %s);
        """, (nombre, descripcion, nombre_imagen))

        conexion.commit()
        cursor.close()
        conexion.close()

        return redirect(url_for('admin_productos'))

    except Exception as e:
        print("Error creando sabor:", e)
        return "Error al crear sabor", 500

@app.route('/crear_topping', methods=['POST'])
def crear_topping():
    if "usuario_id" not in session or session.get("usuario_tipo") != 1:
        return redirect(url_for('login'))

    nombre = request.form.get('nombre')

    if nombre.lower() == "sin topping":
        return redirect(url_for('admin_productos'))

    imagen = request.files.get('imagen')
    nombre_imagen = None

    if imagen and imagen.filename != '' and allowed_file(imagen.filename):
        nombre_imagen = secure_filename(imagen.filename)
        ruta = os.path.join('static', 'img', nombre_imagen)
        imagen.save(ruta)

    try:
        conexion = conectar_bd()
        cursor = conexion.cursor()

        cursor.execute("""
            INSERT INTO public."Toppings"
            ("Nombre_toppings", "Imagen")
            VALUES (%s, %s);
        """, (nombre, nombre_imagen))

        conexion.commit()
        cursor.close()
        conexion.close()

        return redirect(url_for('admin_productos'))

    except Exception as e:
        print("Error creando topping:", e)
        return "Error al crear topping", 500

@app.route('/admin/clientes')
def admin_clientes():
    try:
        conexion = conectar_bd()
        cursor = conexion.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT 
                "Id_usuario",
                "Nombre_completo_usuario",
                correo_usuario
            FROM public."Usuarios"
            WHERE "Id_tipo" = 3
            ORDER BY "Id_usuario" DESC;
        """)

        clientes = cursor.fetchall()

        cursor.close()
        conexion.close()

        return render_template('admin/clientes.html', clientes=clientes)

    except Exception as e:
        print("Error cargando clientes:", e)
        return "Error cargando clientes"

@app.route('/admin/reportes')
def admin_reportes():
    conexion = conectar_bd()
    cursor = conexion.cursor(cursor_factory=RealDictCursor)

    # ----------------------
    # Producto más vendido (según veces que aparece en Detalle_factura)
    # ----------------------
    cursor.execute("""
        SELECT p."Nombre_producto", COUNT(df."Id_product_sabor") AS unidades_vendidas
        FROM public."Detalle_factura" df
        JOIN public."Producto_Sabor" ps ON df."Id_product_sabor" = ps."Id_product_sabor"
        JOIN public."Productos" p ON ps."Id_producto" = p."Id_producto"
        GROUP BY p."Nombre_producto"
        ORDER BY unidades_vendidas DESC
        LIMIT 1
    """)
    producto_mas_vendido = cursor.fetchone()

    # ----------------------
    # Sabor más vendido (según veces que aparece en Detalle_factura)
    # ----------------------
    cursor.execute("""
        SELECT s."Nombre_sabor", COUNT(df."Id_product_sabor") AS unidades_vendidas
        FROM public."Detalle_factura" df
        JOIN public."Producto_Sabor" ps ON df."Id_product_sabor" = ps."Id_product_sabor"
        JOIN public."Sabor" s ON ps."Id_sabor" = s."Id_sabor"
        GROUP BY s."Nombre_sabor"
        ORDER BY unidades_vendidas DESC
        LIMIT 1
    """)
    sabor_mas_vendido = cursor.fetchone()

    # ----------------------
    # Todos los productos
    # ----------------------
    cursor.execute("""
        SELECT p."Nombre_producto", COUNT(df."Id_product_sabor") AS unidades_vendidas
        FROM public."Detalle_factura" df
        JOIN public."Producto_Sabor" ps ON df."Id_product_sabor" = ps."Id_product_sabor"
        JOIN public."Productos" p ON ps."Id_producto" = p."Id_producto"
        GROUP BY p."Nombre_producto"
        ORDER BY unidades_vendidas DESC
    """)
    productos_totales = cursor.fetchall()

    # ----------------------
    # Todos los sabores
    # ----------------------
    cursor.execute("""
        SELECT s."Nombre_sabor", COUNT(df."Id_product_sabor") AS unidades_vendidas
        FROM public."Detalle_factura" df
        JOIN public."Producto_Sabor" ps ON df."Id_product_sabor" = ps."Id_product_sabor"
        JOIN public."Sabor" s ON ps."Id_sabor" = s."Id_sabor"
        GROUP BY s."Nombre_sabor"
        ORDER BY unidades_vendidas DESC
    """)
    sabores_totales = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template(
        'admin/reportes.html',
        producto_mas_vendido=producto_mas_vendido,
        sabor_mas_vendido=sabor_mas_vendido,
        productos_totales=productos_totales,
        sabores_totales=sabores_totales
    )


@app.route('/admin/trabajadores', methods=['GET', 'POST'])
def admin_trabajadores():
    conexion = conectar_bd()
    cursor = conexion.cursor(cursor_factory=RealDictCursor)

    if request.method == 'POST':
        id_usuario = request.form.get('Id_usuario')
        nuevo_tipo = request.form.get('Id_tipo')  # 2 = Trabajador, 3 = Cliente

        try:
            cursor.execute("""
                UPDATE public."Usuarios"
                SET "Id_tipo" = %s
                WHERE "Id_usuario" = %s
            """, (nuevo_tipo, id_usuario))
            conexion.commit()
        except Exception as e:
            conexion.rollback()
            return f"Error actualizando tipo de usuario: {e}"

    cursor.execute("""
        SELECT "Id_usuario", "Nombre_completo_usuario", "correo_usuario", "Id_tipo"
        FROM public."Usuarios"
        ORDER BY "Id_usuario"
    """)
    usuarios = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template('admin/trabajadores.html', usuarios=usuarios)

# ======================================================
# PANEL TRABAJADORES
# ======================================================

@app.route('/panel_trabajadores')
def panel_trabajadores():
    return render_template('panel_trabajadores.html')



# ======================================================
# RUTA PARA LISTAR CONTACTOS (ADMIN / API)
# ======================================================
@app.route('/ver_contactos', methods=['GET'])
def ver_contactos():
    try:
        conexion = conectar_bd()
        if not conexion:
            return jsonify({'error': 'Error al conectar a la base de datos'}), 500

        cursor = conexion.cursor(cursor_factory=RealDictCursor) # Usa RealDictCursor para obtener resultados como diccionarios.
        cursor.execute('SELECT * FROM Contacto ORDER BY creado DESC;') # Consulta para obtener todos los contactos, ordenados por fecha de creación (más reciente primero).
        contactos = cursor.fetchall()
        cursor.close()
        conexion.close()

        # Formatear fecha
        for c in contactos:
            if c.get('creado'): # Formatea el objeto datetime a una cadena con formato 'YYYY-MM-DD HH:MM:SS'.
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
    if "usuario_id" not in session: # Requiere que el usuario esté logueado.
        return jsonify({'error': 'Debes iniciar sesión'}), 401

    datos = request.get_json()
    actual = datos.get("actual", "").strip()
    nueva = datos.get("nueva", "").strip()

    if not actual or not nueva:
        return jsonify({'error': 'Todos los campos son obligatorios'}), 400

    conexion = conectar_bd()
    cursor = conexion.cursor(cursor_factory=RealDictCursor)
# 1. Obtener la contraseña hasheada actual del usuario logueado.
    cursor.execute('SELECT "password" FROM public."Usuarios" WHERE "Id_usuario" = %s;',
                (session["usuario_id"],))
    usuario = cursor.fetchone()
# 2. Verificar si la contraseña actual es correcta.
    if not bcrypt.checkpw(actual.encode('utf-8'), usuario["password"].encode('utf-8')):
        return jsonify({'error': 'La contraseña actual es incorrecta'}), 400
# 3. Hashear la nueva contraseña.
    nueva_hash = bcrypt.hashpw(nueva.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
# 4. Actualizar la contraseña en la base de datos.
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
            return render_template('admin/admin_panel.html')

        if usuario["Id_tipo"] == 2:
            return render_template('trabajador/panel_trabajadores.html')
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
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# ======================================================
# EJECUCIÓN
# ======================================================

if __name__ == '__main__':
    app.run(debug=True)
