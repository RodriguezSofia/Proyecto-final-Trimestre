import psycopg2 #libreria para conectar con python

def conectar(): # DEFINE FUNCION
    try:
        conexion = psycopg2.connect(
            host="localhost", 
            database="Heladeria", # nombre de la base de datos
            user="postgres", # el usuario por defecto
            password="123456" 
        )
        print("Conexion exitosa a la base de datos")
        return conexion
    
    except Exception as e: 
        print("Error al conectar a la base de datos:", e)
        return None

if _name_ == "_main_": #Ejecuta el codigo solo si es el archivo principal
    conectar() #llama la funcion para probar la conexion