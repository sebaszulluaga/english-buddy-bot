import os
import time
import json
import threading
from datetime import datetime
import random  # Para meter aleatoriedad interna si la IA se cicla
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

# Función mejorada para cargar usuarios como un diccionario estructurado
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            try:
                data = json.load(f)
                # Si el archivo viejo era una lista simple, lo migramos a diccionario
                if isinstance(data, list):
                    return {str(uid): {"area": "general"} for uid in data}
                return data
            except json.JSONDecodeError:
                return {}
    return {}

# Función para guardar o actualizar el área elegida por el usuario
def save_user_area(user_id, area):
    users = load_users()
    user_id_str = str(user_id)
    
    if user_id_str not in users:
        users[user_id_str] = {}
        
    users[user_id_str]["area"] = area
    
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)
    print(f"🔹 Usuario {user_id} actualizado con área: {area}")

# Función para pedirle a la IA la palabra basada en un área específica
def get_word_by_area(area):
    try:
        # Configurar contextos duros e inyectar un token aleatorio para forzar variedad en la IA
        seed_random = random.randint(1, 1000)
        
        if area == "ciberseguridad":
            enfoque_tecnico = "ciberseguridad, hacking ético, análisis SOC, hardening, firewalls, criptografía o respuesta a incidentes"
            ejemplo_contexto = "un ataque informático, auditoría o mitigación"
        elif area == "negocios":
            enfoque_tecnico = "metodologías ágiles, KPIs de negocio tech, gestión de proyectos de TI, startups, Product Ownership o requerimientos corporativos corporativos"
            ejemplo_contexto = "una reunión con stakeholders, entrega de producto (delivery) o estrategia de negocio"
        else: # ingeniería / general
            enfoque_tecnico = "ingeniería de sistemas, redes de datos, devops, arquitectura de software, bases de datos o cloud computing"
            ejemplo_contexto = "un despliegue en producción, depuración de código o infraestructura cloud"

        prompt = (
            f"Genera una 'Palabra IT del día' en inglés única, específica e indispensable para el área de **{enfoque_tecnico}**. "
            f"Importante: No elijas términos genéricos de otras áreas. La palabra debe estar directamente ligada a {ejemplo_contexto}. "
            f"Identificador único de petición obligatorio para evitar repeticiones: {seed_random}.\n\n"
            "Formatea la respuesta de forma muy limpia y visual usando negritas y emojis en Markdown de la siguiente manera:\n"
            "1. La palabra en inglés (con su pronunciación figurada entre paréntesis en español).\n"
            "2. Su traducción al español.\n"
            "3. Una definición técnica breve y clara orientada al nicho solicitado.\n"
            "4. Un ejemplo de uso real en una frase corporativa/técnica en inglés con su respectiva traducción al español."
        )
        
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8000",
            temperature=0.8 # Subimos temperatura para mayor creatividad y menos duplicados
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"Error generando palabra de la IA para el área {area}: {e}")
        return "💡 *Word of the Day: Pipeline* (pai-plain)\n\n🔹 *Traducción:* Línea de procesos / Canalización\n🔹 *Definición:* Conjunto de procesos automatizados para compilar, probar y desplegar código."

# 2. Hilo secundario para el envío automático diario (Personalizado por área)
def daily_scheduler():
    print("⏳ Programador diario activado en segundo plano...")
    while True:
        now = datetime.now()
        if now.hour == 8 and now.minute == 0:
            users = load_users()
            if users:
                print(f"📢 Enviando palabras matutinas personalizadas a {len(users)} usuarios...")
                for user_id_str, user_info in users.items():
                    try:
                        user_area = user_info.get("area", "general")
                        word_content = get_word_by_area(user_area)
                        
                        word_message = f"🌅 *¡Good morning! Aquí tienes tu palabra técnica recomendada para el área de {user_area.capitalize()}:* \n\n" + word_content
                        bot.send_message(int(user_id_str), word_message, parse_mode="Markdown")
                    except Exception as e:
                        print(f"No se pudo enviar mensaje matutino al usuario {user_id_str}: {e}")
            
            time.sleep(60)
        time.sleep(30)

threading.Thread(target=daily_scheduler, daemon=True).start()


# 3. Manejadores de comandos e interacciones de Telegram
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.chat.id
    # Registrar con área por defecto al inicio
    save_user_area(user_id, "general")
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_word = types.KeyboardButton("🧠 Get a New Word Now")
    markup.add(btn_word)
    
    welcome_text = (
        f"¡Hola, *{message.from_user.first_name}*! 👋 Bienvenido a tu **English Buddy Pro**.\n\n"
        "Te has suscrito automáticamente a las *notificaciones diarias*. Cada mañana a las 8:00 AM te enviaré una "
        "palabra técnica según tu área de interés guardada. 🚀\n\n"
        "Presiona el botón de abajo para elegir tu especialidad y aprender una palabra ahora mismo."
    )
    bot.send_message(user_id, welcome_text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "🧠 Get a New Word Now")
def send_manual_word_menu(message):
    markup = InlineKeyboardMarkup()
    
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

@bot.callback_query_handler(func=lambda call: call.data.startswith("area_"))
def process_area_selection(call):
    area_seleccionada = call.data.split("_")[1]
    chat_id = call.message.chat.id
    
    bot.answer_callback_query(call.id, text=f"Área guardada: {area_seleccionada.capitalize()}")
    bot.send_chat_action(chat_id, 'typing')
    
    # 🌟 PASO CLAVE: Guardamos el interés del usuario en el JSON para el futuro
    save_user_area(chat_id, area_seleccionada)
    
    # Traer la palabra con la IA forzada
    word_content = get_word_by_area(area_seleccionada)
    
    encabezado = f"🎯 *Vocabulario enfocado en: {area_seleccionada.capitalize()}*\n\n"
    bot.send_message(chat_id, encabezado + word_content, parse_mode="Markdown")

print("🤖 Bot corriendo con persistencia de intereses y sistema anti-duplicados...")
bot.infinity_polling()