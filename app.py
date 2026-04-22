from flask import Flask, request, jsonify, render_template, redirect, url_for, session 
from flask_mail import Mail, Message #Se importa para el envio de correos
import psycopg2
from psycopg2.extras import RealDictCursor
import bcrypt #Se importa bcrypt para el hash o no visualizacion de las contraseñas del usuario
import os, uuid
import datetime  #Se importa os para mejor manejo de las variables del entorno
# - uuid: para generar referencias únicas de pedido (ej: PED-A1B2C3D4)
# - datetime: para registrar la fecha y hora de cada pedido
import random # Se importa random para la generacion de  contraseñas temporales.         
import string #En conjunto con random, se usa para la generación de contraseñas temporales
import requests # Se importa para verificar reCAPTCHA
from werkzeug.utils import secure_filename # Se importa para manejar la seguridad de los nombres de archivos subidos.
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

# ======================================================
# CONFIGURACIÓN GENERAL
# ======================================================

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'Dulce_manjar')
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'img') # Carpeta para guardar las imágenes subidas.
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'} #Modolo seguro para permitir solo ciertos tipos de archivos (imágenes) al subir.

DATOS_PAGO = {

    # ── NEQUI ────────────────────────────────────────────────────────
    "nequi": {
        "numero":   "3019283491",          # ← tu número Nequi (ya configurado)
        "titular":  "Nicolk Anelca Diaz Hernandez",      # ← ej: "Juan García"
    },

    # ── PSE / TRANSFERENCIA BANCARIA ────────────────────────────────
    "bancolombia": {
        "banco":    "BANCOLOMBIA",       # ← ej: "Bancolombia"
        "cuenta":   "888-699065-86", # ← ej: "123-456789-00"
        "tipo":     "Ahorros",             # ← "Ahorros" o "Corriente"
        "titular":  "Nicolk Anelca Diaz Hernandez",      # ← nombre del titular
        "cedula":   "1114001814",      # ← ej: "1.234.567.890"
    },

}
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
    'database': os.environ.get('DB_NAME', 'Heladeria_annia'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', '123456'),
    'port': 5432
}

_sqlalchemy_engine = None

def get_sqlalchemy_engine():
    global _sqlalchemy_engine
    if _sqlalchemy_engine is not None:
        return _sqlalchemy_engine

    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        _sqlalchemy_engine = create_engine(database_url)
        return _sqlalchemy_engine

    user = quote_plus(DB_CONFIG['user'])
    password = quote_plus(DB_CONFIG['password'])
    host = DB_CONFIG['host']
    port = DB_CONFIG['port']
    database = DB_CONFIG['database']

    _sqlalchemy_engine = create_engine(
        f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
    )
    return _sqlalchemy_engine

def conectar_bd():
    try:
        return psycopg2.connect(**DB_CONFIG)
    except psycopg2.Error as e:
        print(f"Error al conectar a la base de datos: {e}")
        return None

# ======================================================
# FUNCIONES: RECUPERACIÓN DE CONTRASEÑA
# ======================================================

def generar_codigo_verificacion(length: int = 4):
    """Genera un código numérico de verificación de `length` dígitos."""
    return ''.join(random.choice(string.digits) for _ in range(length))

# ======================================================
# RUTAS PARA PERFIL DE USUARIO
# ======================================================
@app.context_processor
def inject_user():
    usuario = None
    if 'usuario_id' in session:
        usuario = {
            'nombre': session.get('usuario_nombre'),
            
            'correo': session.get('usuario_correo'),
            
            'foto': session.get('usuario_foto') or 'https://i.imgur.com/6VBx3io.png'
        }
    return dict(usuario=usuario)

#editar perfil usuario

@app.route('/actualizar_perfil', methods=['POST'])
def actualizar_perfil():
    if 'usuario_id' not in session:
        return jsonify({'success': False, 'message': 'Sesión no encontrada'}), 401

    datos = request.get_json()
    # Extraemos los datos del JSON enviado por JS
    nuevo_nombre = datos.get('nombre')
    nuevo_correo = datos.get('correo')
    usuario_id = session['usuario_id']
    

    try:
        conn = conectar_bd()
        cur = conn.cursor()
        
        query = """
            UPDATE public."Usuarios" 
            SET "Nombre_completo_usuario" = %s, 
                "correo_usuario" = %s 
            WHERE "Id_usuario" = %s
        """
        cur.execute(query, (nuevo_nombre, nuevo_correo, usuario_id))
        
        conn.commit()
        cur.close()
        conn.close()

        # Actualizamos la sesión para que los cambios se vean al recargar
        session['usuario_nombre'] = nuevo_nombre
        session['usuario_correo'] = nuevo_correo

        return jsonify({'success': True})
    except Exception as e:
        print(f"Error en DB: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


#cambiar foto de perfil

@app.route('/actualizar_foto', methods=['POST'])
def actualizar_foto():
    if 'usuario_id' not in session:
        return jsonify({'success': False, 'error': 'No hay sesión'}), 401
    
    datos = request.get_json()
    foto_url = datos.get('foto_url')
    
    conexion = conectar_bd() 
    cursor = conexion.cursor()
    try:
        cursor.execute('UPDATE public."Usuarios" SET "foto" = %s WHERE "Id_usuario" = %s', 
                       (foto_url, session['usuario_id']))
        conexion.commit()
        
        session['usuario_foto'] = foto_url
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success': False}), 500
    finally:
        cursor.close()
        conexion.close()

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
            SELECT "Id_toppings", "Nombre_toppings", "stock"
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
@app.route("/api/datos-pago")
def datos_pago():
    metodo = request.args.get("metodo", "nequi").lower()

    if metodo == "banco":
        metodo = "bancolombia"

    datos = DATOS_PAGO.get(metodo, DATOS_PAGO["nequi"])

    return jsonify({"metodo": metodo, "datos": datos})

@app.route("/api/ventas-semanales")
def ventas_semanales():
    hoy = datetime.date.today()
    inicio = hoy - datetime.timedelta(days=29)

    query = text("""
        SELECT DATE(f."Fecha") AS fecha, COALESCE(SUM(d."Total"), 0) AS total
        FROM public."Factura" f
        JOIN public."Detalle_factura" d
            ON f."Id_factura" = d."Id_factura"
        WHERE f."Fecha"::date BETWEEN :inicio AND :hoy
        GROUP BY fecha
        ORDER BY fecha;
    """)

    engine = get_sqlalchemy_engine()
    with engine.connect() as conn:
        rows = conn.execute(query, {"inicio": inicio, "hoy": hoy}).fetchall()

    totales_por_fecha = {}
    for row in rows:
        fecha = row._mapping["fecha"]
        total = row._mapping["total"]
        totales_por_fecha[fecha] = float(total or 0)

    labels = []
    data = []
    for i in range(30):
        dia = inicio + datetime.timedelta(days=i)
        labels.append(dia.strftime("%d/%m"))
        data.append(float(totales_por_fecha.get(dia, 0)))

    return jsonify({"labels": labels, "data": data})

@app.route('/confirmar_pedido', methods=['GET', 'POST'])
def confirmar_pedido():  # sourcery skip: low-code-quality
    id_usuario = session.get("usuario_id")
    if not id_usuario:
        return redirect(url_for('login'))

    if request.method == 'POST':
        nombre_destinatario = request.form.get("nombre_destinatario")
        direccion = request.form.get("direccion")
        id_metodo = request.form.get("metodo_pago")

        if not nombre_destinatario or not direccion:
            return "Datos de envío incompletos", 400

        carrito_detalles = [] # Lista para el HTML
        total_acumulado = 0
        carrito_procesar = []
        index = 0
        
        try:
            conexion = conectar_bd()
            # Usamos RealDictCursor para manejar nombres de columnas fácilmente
            cursor = conexion.cursor(cursor_factory=RealDictCursor)

# --- PROCESAR FORMULARIO Y OBTENER NOMBRES ---
            while True: 
                prefix = f"carrito[{index}]"
                id_producto = request.form.get(f"{prefix}[id_producto]")
                if not id_producto:
                    break

                precio = float(request.form.get(f"{prefix}[precio]"))
                
                # 1. Obtenemos los IDs de los sabores desde el formulario
                sabores_ids = [int(s) for s in request.form.getlist(f"{prefix}[sabores]")]

                # 2. NUEVO: Buscamos los NOMBRES de esos sabores en la BD
                nombres_sabores = []
                if sabores_ids:
                    for s_id in sabores_ids:
                        cursor.execute('SELECT "Nombre_sabor" FROM public."Sabor" WHERE "Id_sabor" = %s', (s_id,))
                        sabor_info = cursor.fetchone()
                        if sabor_info:
                            nombres_sabores.append(sabor_info["Nombre_sabor"])
                
                # Convertimos la lista de nombres en un solo texto separado por comas
                texto_sabores = ", ".join(nombres_sabores) if nombres_sabores else "Selección de la casa"

                # 3. Buscamos el nombre del producto
                cursor.execute('SELECT "Nombre_producto" FROM public."Productos" WHERE "Id_producto" = %s', (id_producto,))
                producto_info = cursor.fetchone()
                nombre_p = producto_info["Nombre_producto"] if producto_info else "Helado Personalizado"

                # 4. ACTUALIZADO: Guardamos 'sabores' en el diccionario para el HTML
                carrito_detalles.append({
                    "nombre": nombre_p,
                    "cantidad": 1,
                    "precio_total": precio,
                    "sabores": texto_sabores  # <-- Esto es lo que leerá tu factura.html
                })
                
                total_acumulado += precio

                # (El resto de tu código de inserción en BD permanece igual...)
                carrito_procesar.append({
                    "id_producto": int(id_producto),
                    "sabores": sabores_ids,
                    "precio": precio
                })
                index += 1
                
                
            metodo_texto = request.form.get("metodo_pago")

            mapa_metodos = {
                "efectivo": 1,
                "nequi": 2,
                "bancolombia": 3
            }

            id_metodo = mapa_metodos.get(metodo_texto)
            

            # --- INSERTAR FACTURA ---
            cursor.execute("""
                INSERT INTO public."Factura"(
                    "Fecha", "Id_metodo", "Id_usuario",
                    "Nombre_destinatario", "Direccion_envio"
                )
                VALUES (NOW(), %s, %s, %s, %s)
                RETURNING "Id_factura";
            """, (id_metodo, id_usuario, nombre_destinatario, direccion))
            id_factura = cursor.fetchone()["Id_factura"]
            # generar referencia de pago
            referencia_pago = f"PED-{uuid.uuid4().hex[:8].upper()}"

            # --- INSERTAR DETALLES ---
            for item in carrito_procesar:
                for id_sabor in item["sabores"]:
                    cursor.execute("""
                        SELECT "Id_product_sabor" FROM public."Producto_Sabor"
                        WHERE "Id_producto" = %s AND "Id_sabor" = %s;
                    """, (item["id_producto"], id_sabor))
                    res = cursor.fetchone()
                    if res:
                        cursor.execute("""
                            INSERT INTO public."Detalle_factura"(
                                "Id_factura", "Id_product_sabor", "Id_toppings", "Total"
                            ) VALUES (%s, %s, %s, %s);
                        """, (id_factura, res["Id_product_sabor"], 4, item["precio"]))

                        #RESTAR STOCK DEL TOPPING
                                    # 🔽 RESTAR STOCK DEL TOPPING
                        cursor.execute("""
                            UPDATE public."Toppings"
                            SET "stock" = "stock" - 1
                            WHERE "Id_toppings" = %s;
                        """, (4,))
            conexion.commit()
            cursor.close()
            conexion.close()
            # --- RENDERIZAR CON TODA LA INFO ---
            return render_template("factura.html",id_factura=id_factura, carrito=carrito_detalles, total=total_acumulado, referencia=referencia_pago,  datos_pago=DATOS_PAGO,  )

        except Exception as e:
            if conexion: conexion.rollback()
            print("Error guardando factura:", e)
            return "Error interno", 500

    # Lógica GET 
    conexion = conectar_bd()
    cursor = conexion.cursor(cursor_factory=RealDictCursor)
    cursor.execute('SELECT "Id_metodo", "Nombre_pago" FROM public."Metodos_pago";')
    metodos_pago = cursor.fetchall()
    cursor.close()
    conexion.close()
    return render_template("confirmar_pedido.html", metodos_pago=metodos_pago)
    #datos de pago para cada método 

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


@app.route('/encuentranos')
def encuentranos():
    return render_template('encuentranos.html')

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

        # Verificar reCAPTCHA
        recaptcha_response = datos.get('g-recaptcha-response', '')
        if not recaptcha_response:
            return jsonify({'error': 'Por favor, verifica que no eres un robot'}), 400

        # Verificar con Google reCAPTCHA
        secret_key = '6LdYyb4sAAAAAMTPRKSwc3L7EO-nUPlIt9_BYCLy'  # Reemplaza con tu clave secreta
        verify_url = 'https://www.google.com/recaptcha/api/siteverify'
        response = requests.post(verify_url, data={'secret': secret_key, 'response': recaptcha_response})
        result = response.json()
        if not result.get('success'):
            return jsonify({'error': 'Verificación reCAPTCHA fallida'}), 400

        conexion = conectar_bd()
        if not conexion:
            return jsonify({'error': 'Error al conectar a la base de datos'}), 500

        cursor = conexion.cursor()

        
        sql = """
            INSERT INTO "Contacto" (correo, mensaje, creado, "Id_usuario")
            OVERRIDING SYSTEM VALUE
            VALUES (%s, %s, NOW(), 17)
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

    detalle_pedido = []  #  inicializar vacío

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
            detalle_pedido = cursor.fetchall()  #  aquí ya es lista

        cursor.close()
        conexion.close()

        return render_template('admin/pedidos.html', pedidos=pedidos, detalle_pedido=detalle_pedido)

    except Exception as e:
        print("Error cargando pedidos:", e)
        return "Error interno", 500

@app.route('/admin/productos')
def admin_productos():
   

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


@app.route('/admin/admin_trabajadores', methods=['GET', 'POST'])
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

    return render_template('admin/admin_trabajadores.html', usuarios=usuarios)

# ======================================================
# PANEL TRABAJADORES
# ======================================================

@app.route('/trabajador/panel_trabajadores')
def panel_trabajadores():
    return render_template('/trabajador/panel_trabajadores.html')



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
    direccion = datos.get('direccion', '').strip()
    telefono = datos.get('telefono', '').strip()
    id_ciudad = datos.get('Id_ciudad', '').strip()

    # Validaciones
    if not all([nombre, correo, contrasena, confirmar_contrasena, direccion, telefono, id_ciudad]):
        return jsonify({'error': 'Todos los campos son obligatorios'}), 400

    if contrasena != confirmar_contrasena:
        return jsonify({'error': 'Las contraseñas no coinciden'}), 400

    password_hash = bcrypt.hashpw(contrasena.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    conexion = conectar_bd()
    if not conexion:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500

    try:
        cursor = conexion.cursor()

        # Verificar si el correo ya existe
        cursor.execute('SELECT * FROM public."Usuarios" WHERE "correo_usuario" = %s;', (correo,))
        if cursor.fetchone():
            cursor.close()
            conexion.close()
            return jsonify({'error': 'El correo ya está registrado'}), 400

        # Insertar el usuario con todos los datos
        cursor.execute("""
            INSERT INTO public."Usuarios"
            ("Nombre_completo_usuario", "correo_usuario", "password", direccion, telefono, "Id_ciudad", "Id_tipo")
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING "Id_usuario";
        """, (nombre, correo, password_hash, direccion, telefono, id_ciudad, 3))

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
        
        session["usuario_correo"] = usuario["correo_usuario"]

        session["usuario_foto"] = usuario.get("foto") or "icon.jpg"

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

        # Obtener tipo de usuario
        cursor.execute(
            'SELECT "Id_tipo" FROM public."Usuarios" WHERE "Id_usuario" = %s;',
            (session["usuario_id"],)
        )
        usuario = cursor.fetchone()

        # Consulta de stock bajo
        cursor.execute("""
            SELECT COUNT(*) AS alertas
            FROM public."Toppings"
            WHERE "stock" <= 5;
        """)
        resultado = cursor.fetchone()
        alertas = resultado["alertas"]

        # Ventas de hoy (suma de detalles por factura)
        cursor.execute("""
            SELECT COALESCE(SUM(d."Total"), 0) AS ventas
            FROM public."Factura" f
            JOIN public."Detalle_factura" d
                ON f."Id_factura" = d."Id_factura"
            WHERE f."Fecha" = CURRENT_DATE;
        """)
        ventas_hoy = cursor.fetchone()["ventas"]
        try:
            ventas_hoy_val = int(round(float(ventas_hoy)))
        except Exception:
            ventas_hoy_val = 0
        ventas_hoy_formateadas = f"{ventas_hoy_val:,}".replace(",", ".")

        # Clientes registrados (Id_tipo = 3)
        cursor.execute("""
            SELECT COUNT(*) AS clientes
            FROM public."Usuarios"
            WHERE "Id_tipo" = 3;
        """)
        clientes_registrados = cursor.fetchone()["clientes"]

        cursor.close()
        conexion.close()

        if usuario["Id_tipo"] == 1:
            return render_template(
                'admin/admin_panel.html',
                alertas=alertas,
                ventas=ventas_hoy_formateadas,
                pendientes=0,
                clientes=clientes_registrados
            )

        if usuario["Id_tipo"] == 2:
            return render_template('trabajador/panel_trabajadores.html')

        return redirect(url_for('home'))

    except Exception as e:
        print(f"Error en admin_panel: {e}")
        return "Error interno", 500
# RECUPERACIÓN DE CONTRASEÑA
# ======================================================

@app.route('/recuperacion', methods=['GET', 'POST'])
def recuperacion():
    if request.method == 'GET':
        return render_template('recuperacion.html')

    json_body = request.get_json(silent=True)
    datos = json_body or request.form
    correo = datos.get('correo', '').strip()

    if not correo:
        if json_body:
            return jsonify({'error': 'El correo es obligatorio'}), 400
        return render_template('recuperacion.html', error='El correo es obligatorio')

    conexion = conectar_bd()
    if not conexion:
        if json_body:
            return jsonify({'error': 'Error de conexión a la base de datos'}), 500
        return render_template('recuperacion.html', error='Error de conexión a la base de datos')

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
            if json_body:
                return jsonify({'error': 'El correo no está registrado'}), 404
            return render_template('recuperacion.html', error='El correo no está registrado')

        codigo = generar_codigo_verificacion()

        session['reset_email'] = correo
        session['reset_code'] = codigo
        session['reset_code_expires'] = (datetime.datetime.now() + datetime.timedelta(minutes=10)).isoformat()
        session.pop('reset_code_validated', None)

        # enviar correo
        msg = Message('Código de recuperación - Heladería Annia', recipients=[correo])
        msg.html = f"""
        <html>
            <body style="font-family: Arial; padding: 20px; background-color: #f5f5f5;">
                <div style="max-width: 600px; background:white; padding:30px; border-radius:10px;">
                    <h2 style="color:#FF69B4; text-align:center;">🍦 Heladería Annia</h2>
                    <p>Hola {usuario['Nombre_completo_usuario']},</p>
                    <p>Tu código de verificación es:</p>

                    <div style="background:#fff3cd; padding:18px; border-radius:5px; text-align:center;">
                        <strong style="font-size:22px;">{codigo}</strong>
                    </div>

                    <br>
                    <p>Puedes usarlo en la página de recuperación de contraseña.</p>
                    <a href="{url_for('verificar_codigo', _external=True)}"
                       style="background:#FF69B4; padding:12px 35px; color:white; 
                              text-decoration:none; border-radius:20px; font-weight:bold;">
                       Verificar Código
                    </a>
                </div>
            </body>
        </html>
        """

        mail.send(msg)

        cursor.close()
        conexion.close()

        if json_body:
            return jsonify({'mensaje': 'Código enviado a tu correo', 'redirect': url_for('verificar_codigo')}), 200
        return redirect(url_for('verificar_codigo'))

    except Exception as e:
        print(f"Error en recuperación: {e}")
        conexion.rollback()
        cursor.close()
        conexion.close()
        if json_body:
            return jsonify({'error': 'Error interno del servidor'}), 500
        return render_template('recuperacion.html', error='Error interno del servidor')


@app.route('/recuperacion/verificar', methods=['GET', 'POST'])
def verificar_codigo():
    if request.method == 'GET':
        if not session.get('reset_email'):
            return redirect(url_for('recuperacion'))
        return render_template('verificacion.html')

    json_body = request.get_json(silent=True)
    datos = json_body or request.form
    codigo_enviado = datos.get('codigo')

    # Si el formulario tiene 4 inputs separados, únalos.
    if not codigo_enviado:
        partes = [datos.get(f'digit{i}', '') for i in range(1, 5)]
        codigo_enviado = ''.join(partes)

    codigo_guardado = session.get('reset_code')
    expires = session.get('reset_code_expires')

    if not codigo_guardado or not expires:
        if json_body:
            return jsonify({'error': 'No hay un proceso de recuperación en curso'}), 400
        return render_template('verificacion.html', error='No hay un proceso de recuperación en curso')

    if datetime.datetime.fromisoformat(expires) < datetime.datetime.now():
        session.pop('reset_code', None)
        session.pop('reset_code_expires', None)
        if json_body:
            return jsonify({'error': 'El código ha expirado'}), 400
        return render_template('verificacion.html', error='El código ha expirado')

    if codigo_enviado != codigo_guardado:
        if json_body:
            return jsonify({'error': 'Código inválido'}), 400
        return render_template('verificacion.html', error='Código inválido')

    session['reset_code_validated'] = True
    if json_body:
        return jsonify({'mensaje': 'Código validado', 'redirect': url_for('nueva_contra')}), 200
    return redirect(url_for('nueva_contra'))


@app.route('/recuperacion/nueva_contra', methods=['GET', 'POST'])
def nueva_contra():
    if request.method == 'GET':
        if not session.get('reset_code_validated'):
            return redirect(url_for('recuperacion'))
        return render_template('nueva_contra.html')

    json_body = request.get_json(silent=True)
    datos = json_body or request.form
    nueva = datos.get('nueva', '').strip()
    confirmar = datos.get('confirmar', '').strip()

    if not nueva or not confirmar:
        if json_body:
            return jsonify({'error': 'Debes completar ambos campos'}), 400
        return render_template('nueva_contra.html', error='Debes completar ambos campos')

    if nueva != confirmar:
        if json_body:
            return jsonify({'error': 'Las contraseñas no coinciden'}), 400
        return render_template('nueva_contra.html', error='Las contraseñas no coinciden')

    correo = session.get('reset_email')
    if not correo:
        if json_body:
            return jsonify({'error': 'No hay un proceso de recuperación en curso'}), 400
        return render_template('nueva_contra.html', error='No hay un proceso de recuperación en curso')

    conexion = conectar_bd()
    if not conexion:
        if json_body:
            return jsonify({'error': 'Error de conexión a la base de datos'}), 500
        return render_template('nueva_contra.html', error='Error de conexión a la base de datos')

    try:
        cursor = conexion.cursor()
        password_hash = bcrypt.hashpw(nueva.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute('UPDATE public."Usuarios" SET "password" = %s WHERE "correo_usuario" = %s;', (password_hash, correo))
        conexion.commit()
        cursor.close()
        conexion.close()

        # Limpiar datos de recuperación
        session.pop('reset_email', None)
        session.pop('reset_code', None)
        session.pop('reset_code_expires', None)
        session.pop('reset_code_validated', None)

        if json_body:
            return jsonify({'mensaje': 'Contraseña actualizada', 'redirect': url_for('login')}), 200
        return redirect(url_for('login'))

    except Exception as e:
        print(f"Error al actualizar la contraseña: {e}")
        conexion.rollback()
        cursor.close()
        conexion.close()
        if json_body:
            return jsonify({'error': 'Error interno del servidor'}), 500
        return render_template('nueva_contra.html', error='Error interno del servidor')

#------------CERRAR SESION--------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# ======================================================
# EJECUCIÓN
# ======================================================
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)