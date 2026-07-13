import os
import time
import json
import threading
from datetime import datetime
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

# Nombre del archivo para guardar a los usuarios suscritos
USERS_FILE = "subscribed_users.json"

# Función para cargar usuarios registrados
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

# Función para guardar un nuevo usuario
def save_user(user_id):
    users = load_users()
    if user_id not in users:
        users.append(user_id)
        with open(USERS_FILE, "w") as f:
            json.dump(users, f)
        print(f"🔹 Nuevo usuario registrado: {user_id}")

# Función avanzada para pedirle a la IA la palabra basada en un área específica
def get_word_by_area(area):
    try:
        # Personalizar el enfoque del prompt dependiendo del botón presionado
        enfoque_tecnico = "ingeniería de sistemas, redes, devops, desarrollo de software o cloud computing"
        if area == "ciberseguridad":
            enfoque_tecnico = "ciberseguridad, hacking ético, análisis SOC, hardening, criptografía o respuesta a incidentes"
        elif area == "negocios":
            enfoque_tecnico = "metodologías ágiles, gestión de proyectos de TI, requerimientos de negocio, startups o gerencia de proyectos"

        prompt = (
            f"Genera la 'Palabra IT del día' en inglés específica para el área de **{enfoque_tecnico}**. "
            "Formatea la respuesta de forma muy limpia y visual usando negritas y emojis en Markdown. "
            "Debe incluir estrictamente:\n"
            "1. La palabra en inglés (con su pronunciación figurada entre paréntesis en español).\n"
            "2. Su traducción al español.\n"
            "3. Una definición técnica breve y clara orientada a ese nicho.\n"
            "4. Un ejemplo de uso real en una frase corporativa/técnica en inglés con su traducción al español."
        )
        
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8000",
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"Error generando palabra de la IA para el área {area}: {e}")
        return "💡 *Word of the Day: Hardening* (har-de-ning)\n\n🔹 *Traducción:* Aseguramiento / Robustecimiento\n🔹 *Definición:* El proceso de asegurar un sistema informático reduciendo su superficie de vulnerabilidades."

# 2. Hilo secundario para el envío automático diario (General)
def daily_scheduler():
    print("⏳ Programador diario activado en segundo plano...")
    while True:
        now = datetime.now()
        # Enviar el mensaje automatizado a las 08:00 AM todos los días
        if now.hour == 8 and now.minute == 0:
            users = load_users()
            if users:
                print(f"📢 Enviando palabra diaria a {len(users)} usuarios...")
                # Por defecto, la palabra diaria de la mañana es general de ingeniería
                word_message = "🌅 *¡Good morning! Aquí tienes tu palabra técnica general del día:* \n\n" + get_word_by_area("general")
                
                for user_id in users:
                    try:
                        bot.send_message(user_id, word_message, parse_mode="Markdown")
                    except Exception as e:
                        print(f"No se pudo enviar mensaje al usuario {user_id}: {e}")
            
            time.sleep(60) # Evitar duplicados en el mismo minuto
        time.sleep(30)

# Arrancar el programador en un hilo aparte para que no bloquee al bot
threading.Thread(target=daily_scheduler, daemon=True).start()


# 3. Manejadores de comandos e interacciones de Telegram
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.chat.id
    save_user(user_id)
    
    # Menú inferior persistente clásico
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_word = types.KeyboardButton("🧠 Get a New Word Now")
    markup.add(btn_word)
    
    welcome_text = (
        f"¡Hola, *{message.from_user.first_name}*! 👋 Bienvenido a tu **English Buddy Pro**.\n\n"
        "Te has suscrito automáticamente a las *notificaciones diarias*. Cada mañana a las 8:00 AM te enviaré una "
        "palabra técnica nueva para que nunca dejes de aprender. 🚀\n\n"
        "Si quieres practicar ahora mismo, presiona el botón de abajo y elige tu área de especialidad técnica."
    )
    bot.send_message(user_id, welcome_text, reply_markup=markup, parse_mode="Markdown")

# Cuando el usuario pide una palabra, le desplegamos el menú de especialidades en lugar de mandarla directo
@bot.message_handler(func=lambda message: message.text == "🧠 Get a New Word Now")
def send_manual_word_menu(message):
    markup = InlineKeyboardMarkup()
    
    # Creamos botones callback para atrapar la selección sin cambiar de pantalla
    btn_ciber = InlineKeyboardButton("🔒 Ciberseguridad", callback_data="area_ciberseguridad")
    btn_ing = InlineKeyboardButton("🛠️ Ingeniería de Sistemas", callback_data="area_ingenieria")
    btn_neg = InlineKeyboardButton("💼 Negocios Tech", callback_data="area_negocios")
    
    markup.add(btn_ciber)
    markup.add(btn_ing)
    markup.add(btn_neg)
    
    bot.send_message(
        message.chat.id, 
        "📚 *Selecciona el área técnica en la que deseas entrenar tu vocabulario:*", 
        reply_markup=markup,
        parse_mode="Markdown"
    )

# Capturar y procesar el botón exacto que presionó el usuario
@bot.callback_query_handler(func=lambda call: call.data.startswith("area_"))
def process_area_selection(call):
    # Extraemos la categoría del callback_data
    area_seleccionada = call.data.split("_")[1]
    chat_id = call.message.chat.id
    
    # Mostrar retroalimentación inmediata en la app (pantalla de carga "typing")
    bot.answer_callback_query(call.id, text="Consultando al motor de IA...")
    bot.send_chat_action(chat_id, 'typing')
    
    # Traer la palabra personalizada desde Groq
    word_content = get_word_by_area(area_seleccionada)
    
    # Enviar respuesta final formateada
    encabezado = f"🎯 *Vocabulario enfocado en: {area_seleccionada.capitalize()}*\n\n"
    bot.send_message(chat_id, encabezado + word_content, parse_mode="Markdown")

# Iniciar el bot
print("🤖 Bot de Telegram corriendo con éxito con arquitectura multicategoría...")
bot.infinity_polling()