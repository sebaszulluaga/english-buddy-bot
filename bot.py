import os
import time
import json
import threading
from datetime import datetime
import random
import telebot
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from groq import Groq
from dotenv import load_dotenv

# 1. Cargar variables de entorno
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API = os.getenv("GROQ_API_KEY")

bot = telebot.TeleBot(TOKEN)

# Inicializar Groq con validación por si la API Key falla o no existe
groq_client = None
if GROQ_API:
    try:
        groq_client = Groq(api_key=GROQ_API)
    except Exception as e:
        print(f"⚠️ No se pudo inicializar el cliente de Groq: {e}")

USERS_FILE = "subscribed_users.json"

# ==========================================
# 📚 POOL DE RESPALDO MASIVO Y 100% SEGURO
# ==========================================
PALABRAS_POOL = {
    "ciberseguridad": [
        {"word": "Phishing", "pron": "fi-shing", "trad": "Suplantación de identidad", "def": "Técnica de engaño para adquirir información confidencial de forma fraudulenta.", "ex": "The employee fell for a phishing email.", "ex_trad": "El empleado cayó en un correo de suplantación de identidad."},
        {"word": "Ransomware", "pron": "ran-som-uer", "trad": "Secuestro de datos", "def": "Malware que cifra los archivos de la víctima exigiendo un pago económico.", "ex": "Our systems were locked by a ransomware attack.", "ex_trad": "Nuestros sistemas fueron bloqueados por un ataque de secuestro de datos."},
        {"word": "Handshake", "pron": "jand-sheik", "trad": "Apretón de manos (Conexión)", "def": "Proceso automatizado de negociación entre dos dispositivos para establecer conexión.", "ex": "The TLS handshake failed due to an expired certificate.", "ex_trad": "El protocolo de conexión TLS falló debido a un certificado expirado."},
        {"word": "Hardening", "pron": "jar-den-ing", "trad": "Aseguramiento / Robustecimiento", "def": "Proceso de asegurar un sistema reduciendo su superficie de vulnerabilidades.", "ex": "Server hardening is essential before deployment.", "ex_trad": "El robustecimiento del servidor es esencial antes del despliegue."},
        {"word": "Exploit", "pron": "eks-ploit", "trad": "Fragmento de software malicioso", "def": "Código o técnica que aprovecha una vulnerabilidad para tomar el control de un sistema.", "ex": "The attacker used a zero-day exploit.", "ex_trad": "El atacante usó un exploit de día cero."},
        {"word": "Pentesting", "pron": "pen-tes-ting", "trad": "Pruebas de penetración", "def": "Práctica de atacar sistemas propios para encontrar y solucionar fallas de seguridad.", "ex": "We hired a firm to perform network pentesting.", "ex_trad": "Contratamos una firma para realizar pruebas de penetración en la red."},
        {"word": "Malware", "pron": "mal-uer", "trad": "Software malicioso", "def": "Cualquier programa diseñado con intenciones dañinas para alterar un sistema.", "ex": "Antivirus software detects and removes malware.", "ex_trad": "El software antivirus detecta y remueve software malicioso."},
        {"word": "Breach", "pron": "briich", "trad": "Brecha de seguridad / Filtración", "def": "Incidente donde datos confidenciales son expuestos o robados sin autorización.", "ex": "The data breach exposed millions of user accounts.", "ex_trad": "La filtración de datos expuso millones de cuentas de usuarios."},
        {"word": "Cipher", "pron": "sai-fer", "trad": "Cifrado / Algoritmo criptográfico", "def": "Algoritmo para realizar el cifrado o descifrado de un paquete de información.", "ex": "AES is a secure symmetric cipher.", "ex_trad": "AES es un algoritmo criptográfico simétrico seguro."}
    ],
    "negocios": [
        {"word": "Stakeholder", "pron": "steik-joul-der", "trad": "Parte interesada", "def": "Cualquier persona u organización afectada por las actividades y decisiones de una empresa.", "ex": "We need to update the stakeholders weekly.", "ex_trad": "Necesitamos actualizar a las partes interesadas semanalmente."},
        {"word": "Backlog", "pron": "bak-log", "trad": "Lista de tareas pendientes", "def": "Acumulación priorizada de trabajo o requerimientos por realizar dentro de un proyecto técnico.", "ex": "Let's add this new feature to the product backlog.", "ex_trad": "Agreguemos esta nueva característica a la lista de pendientes del producto."},
        {"word": "Sprint", "pron": "sprint", "trad": "Ciclo de trabajo ágil", "def": "Período corto de tiempo establecido (usualmente 2 semanas) para completar tareas específicas.", "ex": "We planning the goals for the next sprint.", "ex_trad": "Estamos planeando los objetivos para el siguiente ciclo de trabajo."},
        {"word": "Roadmap", "pron": "roud-map", "trad": "Mapa de ruta / Plan estratégico", "def": "Plan visual de alto nivel que describe la evolución planificada de un producto tech.", "ex": "The Q3 roadmap focuses on cloud migration.", "ex_trad": "El mapa de ruta del tercer trimestre se enfoca en la migración a la nube."},
        {"word": "MVP", "pron": "em-vi-pi", "trad": "Producto Mínimo Viable", "def": "Versión básica de un producto con funciones mínimas para validar una idea en el mercado.", "ex": "We launched an MVP to gather early feedback.", "ex_trad": "Lanzamos un MVP para recolectar retroalimentación temprana."},
        {"word": "ROI", "pron": "ar-ou-ai", "trad": "Retorno de inversión", "def": "Métrica financiera usada para evaluar la eficiencia o rentabilidad de una inversión.", "ex": "The ROI of our new software tools is outstanding.", "ex_trad": "El retorno de inversión de nuestras nuevas herramientas de software es sobresaliente."},
        {"word": "Scope creep", "pron": "skoup-criip", "trad": "Corrupción del alcance", "def": "Expansión descontrolada del alcance de un proyecto sin ajustes de presupuesto o tiempo.", "ex": "Clear documentation avoids scope creep.", "ex_trad": "Una documentación clara evita la corrupción del alcance."},
        {"word": "Deliverable", "pron": "di-li-ver-a-bol", "trad": "Entregable", "def": "Cualquier producto, resultado o documento que deba entregarse para finalizar una etapa.", "ex": "The source code is the main deliverable today.", "ex_trad": "El código fuente es el entregable principal hoy."},
        {"word": "KPI", "pron": "kei-pi-ai", "trad": "Indicador clave de rendimiento", "def": "Métrica cuantitativa que mide el nivel de desempeño y éxito de un proceso.", "ex": "Customer retention is our main KPI this year.", "ex_trad": "La retención de clientes es nuestro indicador clave principal este año."}
    ],
    "ingeneria": [
        {"word": "Pipeline", "pron": "pai-plain", "trad": "Línea de procesos automatizados", "def": "Cadena de procesos automatizados para compilar, probar y desplegar código (CI/CD).", "ex": "The CI/CD pipeline failed during testing.", "ex_trad": "La línea de procesos automatizados falló durante las pruebas."},
        {"word": "API", "pron": "ei-pi-ai", "trad": "Interfaz de Programación de Aplicaciones", "def": "Set de reglas y definiciones que permite que dos aplicaciones interactúen entre sí.", "ex": "We connect to the payment gateway via API.", "ex_trad": "Nos conectamos a la pasarela de pagos mediante una API."},
        {"word": "Middleware", "pron": "mi-del-uer", "trad": "Software de capa intermedia", "def": "Capa de software que conecta diferentes aplicaciones o bases de datos para intercambiar datos.", "ex": "The middleware handles authentication logs.", "ex_trad": "El software de capa intermedia maneja los registros de autenticación."},
        {"word": "Refactoring", "pron": "ri-fak-tor-ing", "trad": "Refactorización", "def": "Proceso de reestructurar el código interno existente sin alterar su comportamiento externo.", "ex": "Code refactoring improved application speed.", "ex_trad": "La refactorización del código mejoró la velocidad de la aplicación."},
        {"word": "Debugging", "pron": "di-bag-ing", "trad": "Depuración / Corrección de errores", "def": "Rutina de identificar, rastrear y remover errores o 'bugs' informáticos en un sistema.", "ex": "He spent all afternoon debugging the script.", "ex_trad": "Él pasó toda la tarde depurando el script."},
        {"word": "Deployment", "pron": "di-ploi-ment", "trad": "Despliegue / Lanzamiento", "def": "Proceso de enviar código listo y configurado a un entorno de servidores en producción.", "ex": "The deployment on Render was completely live.", "ex_trad": "El despliegue en Render se encuentra completamente en vivo."},
        {"word": "Framework", "pron": "freim-uerk", "trad": "Marco de trabajo", "def": "Estructura conceptual y tecnológica de soporte para desarrollo ágil de software.", "ex": "Django is a popular Python framework.", "ex_trad": "Django es un marco de trabajo de Python muy popular."},
        {"word": "Query", "pron": "kue-ri", "trad": "Consulta (Base de datos)", "def": "Petición precisa de información dirigida de forma estructurada a una base de datos.", "ex": "This SQL query optimizes data fetching.", "ex_trad": "Esta consulta SQL optimiza la obtención de datos."},
        {"word": "Overhead", "pron": "ou-ver-jed", "trad": "Sobrecarga de procesamiento", "def": "Tiempo o recursos excesivos consumidos por el sistema para ejecutar tareas de control.", "ex": "Too many microservices can increase network overhead.", "ex_trad": "Demasiados microservicios pueden incrementar la sobrecarga de la red."}
    ]
}

# ==========================================
# 💾 GESTIÓN INTEGRAL DE USUARIOS E HISTORIAL
# ==========================================
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            try:
                data = json.load(f)
                if isinstance(data, list):
                    return {str(uid): {"area": None, "history": []} for uid in data}
                return data
            except json.JSONDecodeError:
                return {}
    return {}

def save_user_data(user_id, area=None, word_seen=None):
    users = load_users()
    user_id_str = str(user_id)
    
    if user_id_str not in users:
        users[user_id_str] = {"area": None, "history": []}
        
    if "history" not in users[user_id_str]:
        users[user_id_str]["history"] = []
        
    if area is not None:
        users[user_id_str]["area"] = area
        
    if word_seen is not None and word_seen not in users[user_id_str]["history"]:
        users[user_id_str]["history"].append(word_seen)
        
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def get_user_info(user_id):
    users = load_users()
    return users.get(str(user_id), {"area": None, "history": []})

# ==========================================
# 🧠 SISTEMA INTELIGENTE ANTI-REPETICIÓN
# ==========================================
def get_word_by_area(user_id, area):
    user_info = get_user_info(user_id)
    history = user_info.get("history", [])
    
    # Normalizar área por si acaso
    if area not in PALABRAS_POOL:
        area = "ingeneria"
        
    # Convertir el historial a una cadena de texto para decírselo a Groq
    palabras_vistas = ", ".join(history) if history else "ninguna"
    
    # Definir los filtros de contexto para el Prompt
    if area == "ciberseguridad":
        enfoque_tecnico = "ciberseguridad, hacking ético, análisis SOC, firewalls o criptografía"
    elif area == "negocios":
        enfoque_tecnico = "metodologías ágiles, KPIs de TI, gestión de proyectos de software o producto"
    else:
        enfoque_tecnico = "ingeniería de software, devops, bases de datos, redes o cloud computing"

    # --- INTENTO 1: LLAMAR A LA INTELIGENCIA ARTIFICIAL (GROQ) ---
    if groq_client:
        try:
            seed_random = random.randint(1, 99999)
            prompt = (
                f"Eres un profesor de inglés técnico de TI. Genera una única 'Palabra IT del día' en inglés "
                f"que sea EXCLUSIVA del área de: {enfoque_tecnico}.\n"
                f"CRÍTICO: No repitas NINGUNA de estas palabras ya vistas por el usuario: [{palabras_vistas}].\n"
                f"ID de variación única: {seed_random}.\n\n"
                "Formatea la respuesta usando negritas y emojis en Markdown exactamente con esta estructura:\n\n"
                "💡 *Word of the Day:* [Palabra] ([Pronunciación en español])\n\n"
                "🔹 *Traducción:* [Traducción]\n"
                "🔹 *Definición:* [Definición técnica clara]\n"
                "🔹 *Ejemplo:* [Frase real corporativa en inglés técnico]\n"
                "🔹 *Traducción del ejemplo:* [Traducción de la frase]"
            )
            
            chat_completion = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama3-8b-8000",
                temperature=0.9
            )
            
            respuesta_ia = chat_completion.choices[0].message.content
            
            # Intentar extraer la palabra generada para guardarla en el historial
            # Buscamos la línea que tiene 'Word of the Day:'
            try:
                linea_palabra = [line for line in respuesta_ia.split('\n') if "Word of the Day:" in line][0]
                palabra_detectada = linea_palabra.split('*Word of the Day:*')[1].split('(')[0].strip()
                save_user_data(user_id, word_seen=palabra_detectada)
            except:
                # Si el formato cambia un poco, guardamos un token genérico para que cuente en el historial
                save_user_data(user_id, word_seen=f"ia_word_{seed_random}")
                
            print(f"✨ Palabra generada exitosamente con Groq para {area}")
            return respuesta_ia

        except Exception as e:
            print(f"⚠️ Groq falló o dio timeout ({e}). Activando respaldo local...")

    # --- INTENTO 2: RESPALDO LOCAL (Si Groq falla) ---
    pool_disponible = PALABRAS_POOL[area]
    palabras_nuevas = [p for p in pool_disponible if p["word"].lower() not in [w.lower() for w in history]]
    
    if not palabras_nuevas:
        # Reiniciar historial si ya vio todas las del pool local
        users = load_users()
        if str(user_id) in users:
            users[str(user_id)]["history"] = []
            with open(USERS_FILE, "w") as f:
                json.dump(users, f, indent=4)
        palabras_nuevas = pool_disponible

    item_elegido = random.choice(palabras_nuevas)
    save_user_data(user_id, word_seen=item_elegido["word"])
    
    formato_local = (
        f"💡 *Word of the Day:* {item_elegido['word']} ({item_elegido['pron']}) [Local Pool] 🛡️\n\n"
        f"🔹 *Traducción:* {item_elegido['trad']}\n"
        f"🔹 *Definición:* {item_elegido['def']}\n"
        f"🔹 *Ejemplo:* _{item_elegido['ex']}_\n"
        f"🔹 *Traducción del ejemplo:* {item_elegido['ex_trad']}"
    )
    return formato_local

# ==========================================
# 🔄 PROGRAMADOR Y RUTINAS AUTOMÁTICAS
# ==========================================
def daily_scheduler():
    while True:
        now = datetime.now()
        if now.hour == 8 and now.minute == 0:
            users = load_users()
            if users:
                for user_id_str, user_info in users.items():
                    try:
                        user_area = user_info.get("area", "ingeneria") or "ingeneria"
                        word_content = get_word_by_area(int(user_id_str), user_area)
                        word_message = f"🌅 *¡Good morning! Tu palabra técnica recomendada para {user_area.upper()}:* \n\n" + word_content
                        bot.send_message(int(user_id_str), word_message, parse_mode="Markdown")
                    except Exception as e:
                        print(f"Error en envío automático: {e}")
            time.sleep(60)
        time.sleep(30)

threading.Thread(target=daily_scheduler, daemon=True).start()


# ==========================================
# ⌨️ TECLADOS Y MENÚS DE CONTROL
# ==========================================
def desplegar_menu_areas(chat_id, texto_guia):
    markup = InlineKeyboardMarkup()
    btn_ciber = InlineKeyboardButton("🔒 Ciberseguridad", callback_data="set_ciberseguridad")
    btn_ing = InlineKeyboardButton("🛠️ Ingeniería de Sistemas", callback_data="set_ingeneria")
    btn_neg = InlineKeyboardButton("💼 Negocios Tech", callback_data="set_negocios")
    markup.add(btn_ciber)
    markup.add(btn_ing)
    markup.add(btn_neg)
    bot.send_message(chat_id, texto_guia, reply_markup=markup, parse_mode="Markdown")


# ==========================================
# 📥 CONTROLADORES DE COMANDOS (TELEGRAM)
# ==========================================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.chat.id
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_word = types.KeyboardButton("🧠 Get a New Word Now")
    btn_change = types.KeyboardButton("⚙️ Cambiar Área de Interés")
    markup.add(btn_word, btn_change)
    
    welcome_text = (
        f"¡Hola, *{message.from_user.first_name}*! 👋 Bienvenido a **English Buddy Pro**.\n\n"
        "Cada mañana a las 8:00 AM te enviaré una palabra automatizada según tu perfil. 🚀\n\n"
        "Presiona el botón de abajo para empezar."
    )
    bot.send_message(user_id, welcome_text, reply_markup=markup, parse_mode="Markdown")
    
    user_info = get_user_info(user_id)
    if user_info.get("area") is None:
        desplegar_menu_areas(user_id, "📚 *Para empezar, selecciona tu área de especialización técnica:*")


# 💥 EL MANEJADOR INTELIGENTE DE PALABRAS AL AZAR SIN REPETICIÓN
@bot.message_handler(func=lambda message: message.text == "🧠 Get a New Word Now")
def handle_word_request(message):
    chat_id = message.chat.id
    user_info = get_user_info(chat_id)
    area_guardada = user_info.get("area")
    
    if area_guardada is None:
        desplegar_menu_areas(chat_id, "⚠️ No has seleccionado un área aún. Por favor elige una:")
        return
        
    bot.send_chat_action(chat_id, 'typing')
    
    # Llamar a la función que saca una palabra al azar y valida el historial
    word_content = get_word_by_area(chat_id, area_guardada)
    
    encabezado = f"🎯 *Vocabulario de hoy enfocado en: {area_guardada.capitalize()}*\n\n"
    bot.send_message(chat_id, encabezado + word_content, parse_mode="Markdown")


@bot.message_handler(func=lambda message: message.text == "⚙️ Cambiar Área de Interés")
def handle_change_area(message):
    desplegar_menu_areas(message.chat.id, "🔄 *Selecciona tu nueva área técnica de preferencia:*")


@bot.callback_query_handler(func=lambda call: call.data.startswith("set_"))
def process_area_setting(call):
    nueva_area = call.data.split("_")[1]
    chat_id = call.message.chat.id
    
    # Registrar el área manteniendo intacto el historial anterior
    save_user_data(chat_id, area=nueva_area)
    
    bot.answer_callback_query(call.id, text=f"Perfil configurado: {nueva_area.capitalize()}")
    
    bot.send_message(chat_id, f"✅ ¡Área configurada con éxito en: *{nueva_area.capitalize()}*!\nDe ahora en adelante recibirás palabras directas de este nicho.", parse_mode="Markdown")
    
    bot.send_chat_action(chat_id, 'typing')
    word_content = get_word_by_area(chat_id, nueva_area)
    bot.send_message(chat_id, f"🎯 *Aquí tienes tu primera palabra:* \n\n" + word_content, parse_mode="Markdown")


print("🤖 Bot corriendo en modo híbrido infalible (Pool Local + Anti-Repetición por Usuario)...")
bot.infinity_polling()