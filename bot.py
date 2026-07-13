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
groq_client = Groq(api_key=GROQ_API)

USERS_FILE = "subscribed_users.json"

# Función para cargar usuarios (Diccionario persistente)
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            try:
                data = json.load(f)
                if isinstance(data, list):
                    return {str(uid): {"area": None} for uid in data}
                return data
            except json.JSONDecodeError:
                return {}
    return {}

# Función para guardar o actualizar el área de interés
def save_user_area(user_id, area):
    users = load_users()
    user_id_str = str(user_id)
    
    if user_id_str not in users:
        users[user_id_str] = {}
        
    users[user_id_str]["area"] = area
    
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)
    print(f"🔹 Área guardada para {user_id}: {area}")

# Función para obtener el área actual del usuario
def get_user_area(user_id):
    users = load_users()
    user_id_str = str(user_id)
    if user_id_str in users:
        return users[user_id_str].get("area", None)
    return None

# Función optimizada con prompts estrictos para evitar repeticiones
def get_word_by_area(area):
    try:
        # Forzar un número aleatorio para que la IA no recicle respuestas de caché
        seed_random = random.randint(1, 99999)
        
        # Filtros estrictos por área para Groq
        if area == "ciberseguridad":
            enfoque_tecnico = "ciberseguridad, hacking ético, análisis SOC, firewalls o criptografía"
            ejemplos = "SIEM, Phishing, Ransomware, Exploit, Zero-day, Handshake, Pentesting o MFA"
        elif area == "negocios":
            enfoque_tecnico = "metodologías ágiles, KPIs de TI, gestión de proyectos de software o producto"
            ejemplos = "Stakeholder, Backlog, Sprint, Roadmap, MVP, ROI, Scope creep o Deliverable"
        else:
            enfoque_tecnico = "ingeniería de software, devops, bases de datos, redes o cloud computing"
            ejemplos = "API, Pipeline, Middleware, Docker, Kubernetes, Refactoring, Microservices o Query"

        # Construcción limpia del prompt sin saltos de línea conflictivos en los f-strings
        prompt = (
            f"Genera una 'Palabra IT del día' en inglés única y exclusiva para el área de {enfoque_tecnico}. "
            f"Puedes inspirarte en conceptos como: {ejemplos}. ID único de variación: {seed_random}. "
            "Formatea la respuesta usando negritas y emojis en Markdown exactamente con esta estructura:\n\n"
            "💡 *Word of the Day:* [Palabra en inglés] ([Pronunciación en español entre paréntesis])\n\n"
            "🔹 *Traducción:* [Traducción al español]\n"
            "🔹 *Definición:* [Definición técnica breve y clara orientada al área]\n"
            "🔹 *Ejemplo:* [Frase real y corporativa en inglés técnico]\n"
            "🔹 *Traducción del ejemplo:* [Traducción de la frase al español]"
        )
        
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8000",
            temperature=1.0  # Máxima creatividad para evitar palabras repetidas por completo
        )
        
        respuesta_ia = chat_completion.choices[0].message.content
        return respuesta_ia

    except Exception as e:
        print(f"❌ Error en la llamada de Groq: {e}")
        # Retornos de emergencia dinámicos por si falla la red o las credenciales
        fallback_words = {
            "ciberseguridad": "💡 *Word of the Day: Ransomware* (ran-som-uer)\n\n🔹 *Traducción:* Secuestro de datos\n🔹 *Definición:* Malware que cifra los archivos de la víctima exigiendo un pago.",
            "negocios": "💡 *Word of the Day: Backlog* (bak-log)\n\n🔹 *Traducción:* Lista de tareas pendientes\n🔹 *Definición:* Acumulación de trabajo o requerimientos prioritarios por hacer.",
            "ingeneria": "💡 *Word of the Day: API* (ei-pi-ai)\n\n🔹 *Traducción:* Interfaz de Programación de Aplicaciones\n🔹 *Definición:* Set de reglas que permite que dos softwares se comuniquen entre sí."
        }
        return fallback_words.get(area, fallback_words["ingeneria"])
    
# Scheduler diario matutino automático
def daily_scheduler():
    while True:
        now = datetime.now()
        if now.hour == 8 and now.minute == 0:
            users = load_users()
            if users:
                for user_id_str, user_info in users.items():
                    try:
                        user_area = user_info.get("area", "ingeneria") or "ingeneria"
                        word_content = get_word_by_area(user_area)
                        word_message = f"🌅 *¡Good morning! Tu palabra técnica recomendada para {user_area.upper()}:* \n\n" + word_content
                        bot.send_message(int(user_id_str), word_message, parse_mode="Markdown")
                    except Exception as e:
                        print(f"Error en envío automático: {e}")
            time.sleep(60)
        time.sleep(30)

threading.Thread(target=daily_scheduler, daemon=True).start()


# 3. Teclados y Menús
def desplegar_menu_areas(chat_id, texto_guia):
    markup = InlineKeyboardMarkup()
    btn_ciber = InlineKeyboardButton("🔒 Ciberseguridad", callback_data="set_ciberseguridad")
    btn_ing = InlineKeyboardButton("🛠️ Ingeniería de Sistemas", callback_data="set_ingeneria")
    btn_neg = InlineKeyboardButton("💼 Negocios Tech", callback_data="set_negocios")
    markup.add(btn_ciber)
    markup.add(btn_ing)
    markup.add(btn_neg)
    bot.send_message(chat_id, texto_guia, reply_markup=markup, parse_mode="Markdown")


# Handlers del Bot
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.chat.id
    
    # Teclado inferior estático principal (Ahora incluye la opción de Cambiar Área)
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
    
    # Si es nuevo, le preguntamos el área inmediatamente
    if get_user_area(user_id) is None:
        desplegar_menu_areas(user_id, "📚 *Para empezar, selecciona tu área de especialización técnica:*")


# 🌟 EL NUEVO FLUJO INTELIGENTE QUE SOLICITASTE
@bot.message_handler(func=lambda message: message.text == "🧠 Get a New Word Now")
def handle_word_request(message):
    chat_id = message.chat.id
    area_guardada = get_user_area(chat_id)
    
    # Caso A: Si no tiene área registrada, se la pedimos
    if area_guardada is None:
        desplegar_menu_areas(chat_id, "⚠️ No has seleccionado un área aún. Por favor elige una:")
        return
        
    # Caso B: Si ya tiene área, le enviamos la palabra DIRECTAMENTE sin menús intermedios
    bot.send_chat_action(chat_id, 'typing')
    word_content = get_word_by_area(area_guardada)
    
    encabezado = f"🎯 *Vocabulario de hoy enfocado en: {area_guardada.capitalize()}*\n\n"
    bot.send_message(chat_id, encabezado + word_content, parse_mode="Markdown")


# Handler para cambiar el área manualmente mediante el botón inferior
@bot.message_handler(func=lambda message: message.text == "⚙️ Cambiar Área de Interés")
def handle_change_area(message):
    desplegar_menu_areas(message.chat.id, "🔄 *Selecciona tu nueva área técnica de preferencia:*")


# Procesar la selección de los botones Inline
@bot.callback_query_handler(func=lambda call: call.data.startswith("set_"))
def process_area_setting(call):
    nueva_area = call.data.split("_")[1]
    chat_id = call.message.chat.id
    
    # Guardamos la configuración de forma persistente
    save_user_area(chat_id, nueva_area)
    
    bot.answer_callback_query(call.id, text=f"Perfil configurado: {nueva_area.capitalize()}")
    
    # Confirmamos al usuario el cambio y le entregamos su primera palabra del área seleccionada
    bot.send_message(chat_id, f"✅ ¡Área configurada con éxito en: *{nueva_area.capitalize()}*!\nDe ahora en adelante recibirás palabras directas de este nicho.", parse_mode="Markdown")
    
    bot.send_chat_action(chat_id, 'typing')
    word_content = get_word_by_area(nueva_area)
    bot.send_message(chat_id, f"🎯 *Aquí tienes tu primera palabra:* \n\n" + word_content, parse_mode="Markdown")


print("🤖 Bot optimizado con UX inteligente y segmentación estricta de palabras...")
bot.infinity_polling()