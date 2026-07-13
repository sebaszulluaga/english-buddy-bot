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
        seed_random = random.randint(1, 99999)
        
        # Diccionario de contextos técnicos ultra-específicos para evitar cruces de palabras
        contextos = {
            "ciberseguridad": {
                "enfoque": "ciberseguridad estricta, hacking ético, análisis SOC, firewalls, criptografía, malware o respuesta a incidentes",
                "ejemplo": "amenaza, vulnerabilidad, SIEM, exploit, phishing, ransomware o descifrado",
                "fallback": "🔹 *Word: Phishing* (fi-shing)\n\nTraducción: Suplantación de identidad"
            },
            "negocios": {
                "enfoque": "metodologías ágiles (Scrum/Kanban), KPIs de negocio tech, gestión de proyectos de TI, startups o Product Ownership",
                "ejemplo": "stakeholders, backlog, sprint, ROI, MVP, roadmap o burndown chart",
                "fallback": "🔹 *Word: Stakeholder* (steik-joul-der)\n\nTraducción: Parte interesada"
            },
            "ingeneria": {
                "enfoque": "ingeniería de software pura, arquitectura de sistemas, backend, redes, devops, bases de datos o cloud computing",
                "ejemplo": "API, middleware, microservicios, indexación, debugging, refactorización o dockerización",
                "fallback": "🔹 *Word: Middleware* (mi-del-uer)\n\nTraducción: Software de capa intermedia"
            }
        }
        
        # Si por alguna razón el área es genérica o vacía
        ctx = contextos.get(area, contextos["ingeneria"])

        prompt = (
            f"Eres un profesor de inglés técnico especializado en TI. Genera una única 'Palabra IT del día' en inglés "
            f"que sea EXCLUSIVA del área de: {ctx['enfoque']}. No uses palabras comunes de administración o desarrollo general.\n"
            f"La palabra DEBE estar directamente relacionada con conceptos como: {ctx['ejemplo']}.\n"
            f"Código único de variación en tiempo real: {seed_random}.\n\n"
            "Formatea la respuesta en Markdown limpio empleando emojis y negritas:\n"
            "1. La palabra en inglés (con su pronunciación figurada entre paréntesis).\n"
            "2. Su traducción al español.\n"
            "3. Una definición técnica concisa y profunda adaptada al nicho.\n"
            "4. Un ejemplo de uso real en una frase en inglés técnico con su respectiva traducción."
        )
        
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8000",
            temperature=0.9,  # Alta creatividad para romper bucles de palabras repetidas
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"Error en la llamada de Groq: {e}")
        return ctx["fallback"]

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