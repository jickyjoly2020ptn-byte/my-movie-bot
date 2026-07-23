# -*- coding: utf-8 -*-
import os
import threading
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- CONFIGURATION ---
BOT_TOKEN = "8905382319:AAF21E4c6NknQGF4OoApB2BQuNmSGxc4MLI"
MONGO_URI = "mongodb+srv://jickyjoly2020ptn_db_user:Gjs8K6RCh8PASscG@cluster0.uiuftrc.mongodb.net/?appName=Cluster0"

bot = telebot.TeleBot(BOT_TOKEN)
client = MongoClient(MONGO_URI)
db = client['movie_bot_db']  
collection = db['series_movies']  

ADMIN_ID = 2043111276  

# --- RENDER PORT BINDING ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"Health check server running on port {port}")
    server.serve_forever()

# --- FUNCTIONS ---

def auto_delete_and_replace(chat_id, sent_msg_id, movie_keyword):
    try:
        bot.delete_message(chat_id, sent_msg_id)
        markup = InlineKeyboardMarkup()
        btn = InlineKeyboardButton(text="🔄 GET FILE AGAIN!", callback_data=f"list_{movie_keyword}")
        markup.add(btn)
        bot.send_message(
            chat_id,
            "---------------------------------------------\n"
            "⚠️ YOUR VIDEO / FILE IS SUCCESSFULLY DELETED !!\n\n"
            "ဗီဒီယိုဖိုင်ကို မူပိုင်ခွင့်အရ ဖြတ်တောက်လိုက်ပါပြီ။\n"
            "ဇာတ်လမ်းတွဲ အပိုင်းများကို ပြန်ကြည့်ရန် အောက်က ခလုတ်ကို နှိပ်ပါ။\n"
            "---------------------------------------------",
            reply_markup=markup
        )
    except Exception as e:
        print("Error in auto-delete:", e)

def show_episode_buttons(chat_id, movie_keyword):
    movie_data = collection.find_one({"keyword": movie_keyword})
    if movie_data and "episodes" in movie_data:
        markup = InlineKeyboardMarkup(row_width=2)
        episodes = movie_data["episodes"]
        buttons = []
        for ep_name in sorted(episodes.keys()):
            btn = InlineKeyboardButton(text=f"🎥 {ep_name.upper()}", callback_data=f"play_{movie_keyword}_{ep_name}")
            buttons.append(btn)
        markup.add(*buttons)
        movie_title = movie_data.get("title", movie_keyword.upper())
        bot.send_message(chat_id, f"🎬 **{movie_title}** ဇာတ်လမ်းတွဲ၏ ကြည့်ရှုလိုသော အပိုင်းကို ရွေးချယ်ပါ -", parse_mode="Markdown", reply_markup=markup)
    else:
        bot.send_message(chat_id, "❌ ကြည့်ရှုလိုသော လင့်ခ်မှာ သက်တမ်းကုန်ဆုံးသွားပြီ သို့မဟုတ် ရှာမတွေ့တော့ပါ။")

# --- HANDLERS ---

@bot.message_handler(commands=['start'])
def handle_start(message):
    args = message.text.split()
    if len(args) > 1:
        movie_keyword = args[1].lower()
        show_episode_buttons(message.chat.id, movie_keyword)
    else:
        bot.send_message(message.chat.id, "👋 မင်္ဂလာပါ။ ဇာတ်လမ်းတွဲများ ကြည့်ရှုရန်အတွက် Channel ထဲက လင့်ခ်များမှတစ်ဆင့် ဝင်ရောက်ပေးပါရန်။")

@bot.callback_query_handler(func=lambda call: call.data.startswith('play_'))
def handle_play_video(call):
    _, movie_keyword, ep_name = call.data.split('_')
    movie_data = collection.find_one({"keyword": movie_keyword})
    if movie_data and "episodes" in movie_data and ep_name in movie_data["episodes"]:
        video_file_id = movie_data["episodes"][ep_name]
        chat_id = call.message.chat.id
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        caption_text = f"🎬 {movie_keyword.upper()} - {ep_name.upper()}\n\n⚠️ ဒီဗီဒီယိုဖိုင်သည် မူပိုင်ခွင့်ကြောင့် ၅ မိနစ်အတွင်း အလိုအလျောက် ပျက်သွားပါမည်။"
        sent_video = bot.send_video(chat_id, video_file_id, caption=caption_text)
        threading.Timer(300, auto_delete_and_replace, args=[chat_id, sent_video.message_id, movie_keyword]).start()

@bot.callback_query_handler(func=lambda call: call.data.startswith('list_'))
def handle_show_list_again(call):
    _, movie_keyword = call.data.split('_')
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    show_episode_buttons(call.message.chat.id, movie_keyword)

# --- BOT RUNNING ---
if __name__ == "__main__":
    print("Auto-Delete Movie Bot is running...")
    bot.delete_webhook()  
    
    # Port Binding Server ကို နှိုးခြင်း
    threading.Thread(target=run_health_server, daemon=True).start()
    
    bot.infinity_polling()
