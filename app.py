from flask import Flask, request, jsonify, send_file
import psycopg2
from psycopg2.extras import RealDictCursor
import os #permite que el progrma trabaje con archivos del sistema operativo
import datetime

#configuracion de la aplicacion

app = Flask(__name__)

DB_CONFIG = {
    'host': 'localhost',
    'database': 'Heladeria',
    'user': 'postgres',
    'password': '123456',
    'port': 5432,
    
}
#funcion para conectar la base de datos
def conectar_bd():
    try:
        conexion = psycopg2.connect(**DB_CONFIG)
        return conexion
    except psycopg2.Error as e:
        print(f"Error al conectar a la base de datos a postgres: {e}")
        return None

#pagina principal index.html
@app.route('/')
def inicio():
    return send_file('index.html')

#ruta para guardar los campos que se requieren en el formulario
@app.route('/contacto', methods=['POST']) #post para que tome todos los campos del formulario
def guardar_contactos():
    try:
        datos = request.get_json() #obtener los datos en formato json
        nombre = datos.get('nombre', '').strip()
        email = datos.get('email', '').strip()
        mensaje = datos.get('mensaje', '').strip()
        if not nombre or not email:
            return jsonify({'error': 'Nombre y email son obligatorios.'}), 400 #codigo 400: solicitud incorrecta
        cursor=conexion.cursor()
        
        sql_insertar = """
        INSERT INTO contactos (nombre, email, mensaje)
        VALUE (%s, %s, %s)"""
        cursor.execute(sql_insertar, (nombre, email, mensaje))
        
        contacto_id=cursor.fetchone()[0] #obtener el id del contacto insertado
        conexion.commit()
        cursor.close()
        return jsonify({'mensaje': 'Contacto guardado exitosamente.', 'contacto_id': contacto_id}), 201 #codigo 201: recuro se creo correctamente 
    except Exception as e:
        print(f"Error al guardar el contacto: {e}")
        return jsonify({'error': 'Error al procesar la solicitud de datos.'}), 500 #codigo 500: error interno de la bd

#ruta ver todos los contactos 
@app.route('/contactos', methods=['GET'])
def ver_contactos():
    try: #manejo de errores en la conexion
        conexion=conectar_bd() #cargar los datos de postgres
        if conexion is None: #devuelve un parametro
            return jsonify({'error': 'No se pudo conectar a la base de datos.'}), 500 
        cursor = conexion.cursor(cursor_factory=RealDictCursor) #crea un cursor para llamar los datos de la bd y el formato RealDictCursor permite obtener los resultados como diccionarios
        cursor.execute("SELECT * FROM contactos ORDER BY creado DESC") #valida las columnas y trae los datos de una forma descendente
        contactos = cursor.fetchall() 
        cursor.close()
        conexion.close()
        
        for contacto in contactos: #formatear la fecha de creacion
            if contacto['creado']:
                contacto['creado'] = contacto['creado'].strftime('%Y-%m-%d %H:%M:%S')
        return jsonify(contactos), 200 #codigo 200: solicitud exitosa
    except Exception as e:
        print(f"Error al obtener los contactos: {e}")
        return jsonify({'error': 'Error al obtener los contactos'}), 500

#inicio del servidor
if __name__ == '__main__':
    print("Iniciando el servidor...")
    crear_tabla()
    