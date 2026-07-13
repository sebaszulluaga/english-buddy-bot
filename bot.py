import os
import time
import json
import threading
from datetime import datetime
import telebot
from telebot import types
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

# Función para pedirle a la IA la palabra técnica del día
def get_daily_word_from_ai():
    try:
        prompt = (
            "Genera la 'Palabra IT del día' en inglés para profesionales de tecnología. "
            "Formatea la respuesta de forma muy limpia y visual usando negritas y emojis en Markdown. "
            "Debe incluir:\n"
            "1. La palabra en inglés (con su pronunciación figurada entre paréntesis).\n"
            "2. Su traducción al español.\n"
            "3. Una definición técnica breve y clara.\n"
            "4. Un ejemplo de uso real en una frase en inglés técnico con su traducción."
        )
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8000",
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"Error generando palabra de la IA: {e}")
        return "💡 *Word of the Day: Deployment* (de-ploi-ment)\n\n🔹 *Traducción:* Despliegue\n🔹 *Definición:* El proceso de enviar código a un servidor en la nube para que esté disponible al público."

# 2. Hilo secundario para el envío automático diario
def daily_scheduler():
    print("⏳ Programador diario activado en segundo plano...")
    while True:
        now = datetime.now()
        # Puedes configurar aquí la hora exacta que prefieras (Ej: 08:30 AM)
        # Por ahora lo configuramos para enviar el mensaje a las 08:00 AM todos los días
        if now.hour == 8 and now.minute == 0:
            users = load_users()
            if users:
                print(f"📢 Enviando palabra diaria a {len(users)} usuarios...")
                word_message = "🌅 *¡Good morning! Aquí tienes tu palabra técnica del día:* \n\n" + get_daily_word_from_ai()
                
                for user_id in users:
                    try:
                        # parse_mode="Markdown" permite que se vean las negritas y emojis de la IA
                        bot.send_message(user_id, word_message, parse_mode="Markdown")
                    except Exception as e:
                        print(f"No se pudo enviar mensaje al usuario {user_id}: {e}")
            
            # Dormir el hilo por 60 segundos para evitar que envíe el mensaje múltiples veces en el mismo minuto
            time.sleep(60)
        
        # Revisar la hora del sistema cada 30 segundos
        time.sleep(30)

# Arrancar el programador en un hilo aparte para que no bloquee al bot de Telegram
threading.Thread(target=daily_scheduler, daemon=True).start()


# 3. Manejadores de comandos de Telegram
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.chat.id
    # Guardamos automáticamente al usuario en nuestra lista al dar /start
    save_user(user_id)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_word = types.KeyboardButton("🧠 Get a New Word Now")
    markup.add(btn_word)
    
    welcome_text = (
        f"¡Hola, *{message.from_user.first_name}*! 👋 Bienvenido a tu English Buddy Pro.\n\n"
        "Te has suscrito automáticamente a las *notificaciones diarias*. Cada mañana te enviaré una "
        "palabra técnica nueva para que nunca dejes de aprender. 🚀\n\n"
        "Si no quieres esperar a mañana, puedes presionar el botón de abajo para aprender una palabra ahora mismo."
    )
    bot.send_message(user_id, welcome_text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "🧠 Get a New Word Now")
def send_manual_word(message):
    bot.send_chat_action(message.chat.id, 'typing')
    word = get_daily_word_from_ai()
    bot.send_message(message.chat.id, word, parse_mode="Markdown")

# Iniciar el bot
print("🤖 Bot de Telegram corriendo con éxito...")
bot.infinity_polling()