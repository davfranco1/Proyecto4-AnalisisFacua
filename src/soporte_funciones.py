# Librerías para gestión de tiempos
from time import sleep
from tqdm import tqdm

# Librerías para tratamiento de datos

import pandas as pd
import numpy as np

# Librerías para captura de datos
import requests
from bs4 import BeautifulSoup

# Librerías para automatización de navegadores web con Selenium
from selenium import webdriver  
from webdriver_manager.chrome import ChromeDriverManager  
from selenium.webdriver.common.keys import Keys  
from selenium.webdriver.support.ui import Select 
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException 

# Librería para trabajar con bases de datos SQL
import psycopg2
from psycopg2 import OperationalError, errorcodes, errors

# Librería para manejar archivos .env, para cargar tokens y claves
import os
import dotenv
dotenv.load_dotenv()

# Librería para ignorar avisos
import warnings
warnings.filterwarnings("ignore") # Ignora TODOS los avisos


# -------------------------------------- #

# Este script permite navegar y extraer información de un sitio web, limpiar y organizar los datos,
# y luego interactuar con una base de datos para almacenar o recuperar información.
# A continuación un resumen de sus funcionalidades:

# captura_links_facua(url):
# Navega el sitio web de FACUA utilizando Selenium para capturar los enlaces de los productos de supermercados.
# Realiza clics en los diferentes supermercados y categorías para extraer los enlaces de los productos utilizando BeautifulSoup.
# Devuelve una lista de enlaces de productos.

# captura_historicos_facua(lista_links):
# Toma una lista de enlaces de productos y navega cada uno para capturar datos históricos de precios.
# Utiliza BeautifulSoup para extraer las tablas de datos históricos de cada producto.
# Limpia los datos con Pandas y los organiza en un DataFrame que contiene la información histórica de los productos.
# Devuelve un DataFrame con los datos históricos completos.

# dbeaver_conexion(database):
# Establece una conexión a una base de datos DBeaver utilizando psycopg2.
# Incluye manejo de errores para casos como contraseñas incorrectas o problemas de conexión.
# Devuelve un objeto de conexión a la base de datos.

# dbeaver_fetch(conexion, query):
# Ejecuta una consulta SQL y obtiene los resultados desde la base de datos.
# Devuelve los resultados de la consulta en forma de dataframe.

# *dbeaver_commit(conexion, query, values):
# Ejecuta una consulta SQL y realiza un commit de los cambios en la base de datos.
# Devuelve un mensaje de confirmación después del commit.

# *dbeaver_commitmany(conexion, query, values):
# Ejecuta múltiples consultas SQL y realiza un commit de los cambios en la base de datos.
# Devuelve un mensaje de confirmación después del commit.

# -------------------------------------- #


def captura_links_facua(url):
    """
    Captura los enlaces de productos del sitio web de supermercados FACUA.

    Args:
        url (str): La URL del sitio web de FACUA.

    Returns:
        list: Una lista de enlaces de productos.
    """
    driver = webdriver.Chrome()
    url_faqua = "https://super.facua.org"
    driver.get(url_faqua)
    driver.maximize_window()
    driver.find_element("css selector", "#rcc-confirm-button").click()
    print("Click en cookies")
    sleep(2)
    lista_links = []
    lista_fallos = []

    # Entrar a cada supermercado
    for i in tqdm(range(1, 7)):
        driver.execute_script("window.scrollTo(0, 500);")
        sleep(1)
        driver.find_element("css selector", f"body > section:nth-child(4) > div > div.row.gx-4.gx-lg-6.row-cols-2.row-cols-md-2.row-cols-xl-6.justify-content-center > div:nth-child({i}) > div > div.card-footer.p-4.pt-0.border-top-0.bg-transparent > div > a").click()
        print(f"Click en supermercado: {i}")
        sleep(2)
        # Entrar a cada categoría
        for i in range(1, 4):
            driver.execute_script("window.scrollTo(0, 500);")
            sleep(1)
            driver.find_element("css selector", f"body > section:nth-child(4) > div > div.row.gx-4.gx-lg-5.row-cols-2.row-cols-md-3.row-cols-xl-4.justify-content-center > div:nth-child({i}) > div > div.card-footer.p-4.pt-0.border-top-0.border-top-0.bg-transparent > div > a").click()
            print(f"Click en categoría: {i}")
            sleep(2)
            # Extraer los URLs de los productos usando BeautifulSoup
            url_actual = driver.current_url
            try:
                response = requests.get(url_actual)
                soup = BeautifulSoup(response.content, "html.parser")
                for div in soup.findAll("div", {"class": "card-footer p-4 pt-0 border-top-0 bg-transparent"}):
                    etiqueta = div.find("a", href=True)
                    if etiqueta:
                        lista_links.append(etiqueta['href'])
            except:
                lista_fallos.append(url_actual)
                
            driver.back()
        sleep(2)
        driver.back()
        
    driver.close()
    return lista_links


def captura_historicos_facua(lista_links):
    """
    Captura datos históricos de productos desde una lista de URLs.

    Args:
        lista_links (list): Una lista de URLs de productos.

    Returns:
        DataFrame: Un DataFrame que contiene datos históricos de productos.
    """
    df_completo = pd.DataFrame()

    # Para cada link en la lista, realizamos las siguientes operaciones:
    for link in tqdm(lista_links):

        # Si no encuentra la tabla o hay otro error, pasa al siguiente link.
        try:
            url = link
            response = requests.get(url)

            # Se crea la sopa
            soup = BeautifulSoup(response.content, "html.parser")

            # Se busca la tabla y se almacena en un DF
            tabla = soup.find("table")
            encabezados = [encabezado.text.strip() for encabezado in tabla.find_all("th")]
            filas = []
            for fila in tabla.find_all("tr")[1:]:
                campos = fila.find_all("td")
                datos_fila = [campo.text.strip() for campo in campos]
                filas.append(datos_fila)
            df_tabla = pd.DataFrame(filas, columns=encabezados)

            # Se realiza una limpeza y organización inicial de los datos utilizando Pandas
            df_tabla[["Var. Euros", "Var. Porcentaje"]] = df_tabla["Variación"].str.split(" ", expand=True)
            df_tabla.drop(columns="Variación", inplace=True)
            df_tabla["Producto"] = url.split("/")[5].replace("-", " ").title()
            df_tabla["Supermercado"] = url.split("/")[3].capitalize()
            df_tabla["Categoría"] = url.split("/")[4].capitalize()
            df_tabla = df_tabla.rename(columns={"Día": "Fecha"})
            #df_tabla["Fecha"] = pd.to_datetime(df_tabla["Fecha"], format="%d/%m/%Y").dt.strftime("%Y-%m-%d") #está causando DFs vacíos
            df_tabla["Precio (€)"] = df_tabla["Precio (€)"].str.replace(",", ".").apply(float)
            df_tabla = df_tabla.reindex(columns=["Fecha", "Producto", "Precio (€)", "Categoría", "Supermercado", "Var. Euros", "Var. Porcentaje"])

            # Se van concatenando los DFs uno encima del otro.
            df_completo = pd.concat([df_completo, df_tabla], ignore_index=True) # Ignore para mantener índice continuo

        # Gestión de errores
        except Exception as e:
            print(f"Error procesando la URL: {url}, motivo: {e}")

    return df_completo

dbeaver_pw = os.getenv("dbeaver_pw")


def dbeaver_conexion(database):
    """
    Establece una conexión a una base de datos DBeaver.

    Args:
        database (str): El nombre de la base de datos.

    Returns:
        connection: Un objeto de conexión a la base de datos.
    """
    try:
        conexion = psycopg2.connect(
            database=database,
            user="my_user",
            password=dbeaver_pw,
            host="localhost",
            port="5432"
        )
    except OperationalError as e:
        if e.pgcode == errorcodes.INVALID_PASSWORD:
            print("Contraseña es errónea")
        elif e.pgcode == errorcodes.CONNECTION_EXCEPTION:
            print("Error de conexión")
        else:
            print(f"Ocurrió el error {e}")

    return conexion


def dbeaver_fetch(conexion, query):
    """
    Ejecuta una consulta y obtiene los resultados en un dataframe.

    Args:
        conexion (connection): Un objeto de conexión a la base de datos.
        query (str): La consulta SQL a ejecutar.

    Returns:
        list: Los resultados de la consulta en un dataframe.
    """
    cursor = conexion.cursor()
    cursor.execute(query)
    # resultado_query = cursor.fetchall()
    # Si quisiéramos que el resultado fuera en forma de lista podríamos utilizar esta línea de código.
    # En este caso, sin embargo, nos interesa obtener directamente DFs.
    
    df = pd.DataFrame(cursor.fetchall())
    df.columns = [col[0] for col in cursor.description]

    cursor.close()
    conexion.close()

    return df


def dbeaver_commit(conexion, query, *values):
    """
    Ejecuta una consulta y realiza un commit de los cambios.

    Args:
        conexion (connection): Un objeto de conexión a la base de datos.
        query (str): La consulta SQL a ejecutar.
        *values: Los valores a incluir en la consulta.

    Returns:
        str: Un mensaje de confirmación después del commit.
    """
    cursor = conexion.cursor()
    cursor.execute(query, *values)
    conexion.commit()
    cursor.close()
    conexion.close()
    return print("Commit realizado")


def dbeaver_commitmany(conexion, query, *values):
    """
    Ejecuta múltiples consultas y realiza un commit de los cambios.

    Args:
        conexion (connection): Un objeto de conexión a la base de datos.
        query (str): La consulta SQL a ejecutar.
        *values: Los valores a incluir en la consulta.

    Returns:
        str: Un mensaje de confirmación después del commit.
    """
    cursor = conexion.cursor()
    cursor.executemany(query, *values)
    conexion.commit()
    cursor.close()
    conexion.close()
    return print("Commit realizado")