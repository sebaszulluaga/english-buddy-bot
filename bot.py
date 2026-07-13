import os
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from groq import Groq
from dotenv import load_dotenv

# 1. Load the secret tokens
load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# 2. Configure the AI and Bot
client = Groq(api_key=GROQ_API_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# 🧠 3. THE MOCK DATABASE
user_data = {}

# 🎛️ 4. THE MAIN BUTTON DASHBOARD
def generate_main_dashboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("💡 Get a New Word"), KeyboardButton("⚙️ Change My Settings"))
    return markup

# ⚙️ 5. THE SETTINGS INLINE MENU (Now with LATAM Careers)
def generate_settings_menu():
    markup = InlineKeyboardMarkup()
    markup.row_width = 3
    markup.add(
        InlineKeyboardButton("B1", callback_data="level_B1"),
        InlineKeyboardButton("B2", callback_data="level_B2"),
        InlineKeyboardButton("C1", callback_data="level_C1")
    )
    markup.row_width = 1 # One button per row for the careers to keep it clean
    markup.add(
        InlineKeyboardButton("📚 General English", callback_data="track_General"),
        InlineKeyboardButton("💻 IT & Cybersecurity", callback_data="track_IT"),
        InlineKeyboardButton("📊 Business Administration", callback_data="track_Business"),
        InlineKeyboardButton("⚕️ Healthcare & Medicine", callback_data="track_Health"),
        InlineKeyboardButton("🏗️ Engineering", callback_data="track_Engineering")
    )
    return markup

# 6. Handle /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        user_data[chat_id] = {"level": "B2", "track": "General"}
    
    welcome_text = (
        "🤖 **Welcome to English Buddy Pro!**\n\n"
        "Look at the bottom of your screen. Tap the buttons to control the bot—no typing required!"
    )
    bot.send_message(chat_id, welcome_text, reply_markup=generate_main_dashboard(), parse_mode="Markdown")

# 7. Listen for the Button Text clicks
@bot.message_handler(func=lambda message: True)
def handle_text_or_buttons(message):
    chat_id = message.chat.id
    
    if message.text == "💡 Get a New Word":
        bot.send_chat_action(chat_id, 'typing')
        prefs = user_data.get(chat_id, {"level": "B2", "track": "General"})
        level = prefs["level"]
        track = prefs["track"]

        # UPGRADED SYSTEM INSTRUCTIONS: Translation and Pronunciation
        system_instructions = f"You are an English teacher for a {level} level native Spanish speaker. "
        
        if track == "IT":
            system_instructions += "Pick ONE practical vocabulary word heavily used in tech, software, or cybersecurity. "
        elif track == "Business":
            system_instructions += "Pick ONE practical vocabulary word heavily used in Business Administration, finance, or corporate offices. "
        elif track == "Health":
            system_instructions += "Pick ONE practical vocabulary word used in healthcare, medicine, or nursing. "
        elif track == "Engineering":
            system_instructions += "Pick ONE practical vocabulary word used in civil, mechanical, or industrial engineering. "
        else:
            system_instructions += "Pick ONE interesting, practical English word used in daily life. "

        system_instructions += (
            "Explain it simply, and provide a real-world example sentence. "
            "Format your response exactly like this:\n"
            "💡 **Word:** [Word]\n"
            "📢 **Pronunciation:** [Simple phonetic spelling for a Spanish speaker to read]\n"
            "🇪🇸 **Translation:** [Spanish translation]\n"
            "📝 **Definition:** [Simple definition in English]\n"
            "🗣️ **Example:** '[Example sentence in English]'\n"
        )

        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_instructions},
                    {"role": "user", "content": "Give me a vocabulary word."}
                ],
                model="llama-3.1-8b-instant",
            )
            bot.reply_to(message, chat_completion.choices[0].message.content, parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(message, "Oops! I couldn't think of a word right now.")
        return

    elif message.text == "⚙️ Change My Settings":
        bot.send_message(chat_id, "Tap below to adjust your profile:", reply_markup=generate_settings_menu())
        return

    else:
        bot.send_chat_action(chat_id, 'typing')
        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a friendly English teacher. Correct any grammar mistakes gently and briefly in English, then reply to their message to keep the conversation going."
                    },
                    {"role": "user", "content": message.text}
                ],
                model="llama-3.1-8b-instant",
            )
            bot.reply_to(message, chat_completion.choices[0].message.content)
        except Exception as e:
            bot.reply_to(message, "Oops! My brain had a small glitch.")

# 8. Handle Inline Button Clicks
@bot.callback_query_handler(func=lambda call: True)
def handle_inline_clicks(call):
    chat_id = call.message.chat.id
    if chat_id not in user_data:
        user_data[chat_id] = {"level": "B2", "track": "General"}

    if call.data.startswith("level_"):
        new_level = call.data.split("_")[1]
        user_data[chat_id]["level"] = new_level
        bot.answer_callback_query(call.id, f"Level set to {new_level}")
        bot.send_message(chat_id, f"✅ Level updated to **{new_level}**.", parse_mode="Markdown")
        
    elif call.data.startswith("track_"):
        new_track = call.data.split("_")[1]
        user_data[chat_id]["track"] = new_track
        
        # Clean up the name for the confirmation message
        track_names = {
            "General": "General English",
            "IT": "IT & Cybersecurity",
            "Business": "Business Administration",
            "Health": "Healthcare & Medicine",
            "Engineering": "Engineering"
        }
        track_name = track_names.get(new_track, new_track)
        
        bot.answer_callback_query(call.id, f"Track set to {track_name}")
        bot.send_message(chat_id, f"✅ Track updated to **{track_name}**.", parse_mode="Markdown")

# 9. Keep the program running
print("🟢 English Buddy Pro is running! Press Ctrl+C to stop.")
bot.infinity_polling()