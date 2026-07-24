import os
import telebot
import threading
import time
import re
from pymongo import MongoClient
import certifi

# === အချက်အလက်များ တန်းထည့်ရန် ===
BOT_TOKEN = "8038762572:AAG_v6y7sb7YYf7RpH_anVJDJlSZVbpstvY"  # သင့် Bot Token အသစ်
WEBAPP_URL = "https://my-movie-bot-1-ss8q.onrender.com"        # သင့် Render URL အမှန်
ADMIN_IDS = [2043111276]                                      # သင့် Telegram User ID
host_ips = "ac-8w9cptn-shard-00-00.uluftrc.mongodb.net:27017,ac-8w9cptn-shard-00-01.uluftrc.mongodb.net:27017,ac-8w9cptn-shard-00-02.uluftrc.mongodb.net:27017"
options = "?ssl=true&replicaSet=atlas-m0wsp6-shard-00&authSource=admin&retryWrites=true&w=majority&appName=Cluster0"
MONGO_URI = f"mongodb://botuser:jickymovie2026@{host_ips}/{options}"


DELETE_AFTER_SECONDS = 300 
bot = telebot.TeleBot(BOT_TOKEN)

# MongoDB ချိတ်ဆက်ခြင်း
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client['telegram_movie_bot']
movies_collection = db['movies']

# နောက်ကွယ်မှ အလိုအလျောက် ဖျက်ပေးမည့် Function
def auto_delete(chat_id, message_id, delay):
    time.sleep(delay)
    try:
        bot.delete_message(chat_id, message_id)
    except:
        pass

# /start Command
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "👋 မင်္ဂလာပါ! ရုပ်ရှင်နှင့် ဇာတ်လမ်းတွဲများ တောင်းနိုင်တဲ့ Bot ပါ။\n\n"
        "🔍 ဇာတ်လမ်းအမည်ကို ရိုက်ပြီး ရှာဖွေနိုင်ပါတယ်။\n"
        f"⚠️ သတိပေးချက် - ဗီဒီယိုဖိုင်များသည် **{int(DELETE_AFTER_SECONDS / 60)} မိနစ်** အတွင်း အလိုအလျောက် ပြန်ပျက်သွားပါမည်။"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

# === ADMIN စနစ် ===
@bot.message_handler(content_types=['video'], func=lambda message: message.from_user.id in ADMIN_IDS)
def add_movie_by_admin(message):
    if not message.caption:
        bot.reply_to(message, "❌ ကျေးဇူးပြု၍ ဗီဒီယို Caption တွင် ရုပ်ရှင်အမည်ကို ရိုက်ထည့်ပေးပါ။")
        return
    movie_name = message.caption.lower().strip()
    movies_collection.update_one({"movie_name": movie_name}, {"$set": {"file_id": message.video.file_id}}, upsert=True)
    bot.reply_to(message, f"✅ '{movie_name.upper()}' ကို ထည့်သွင်းပြီးပါပြီ။")

# === USER စနစ် ===
@bot.message_handler(func=lambda message: True)
def search_and_send_movie(message):
    user_query = message.text.lower().strip()
    chat_id = message.chat.id
    query_regex = re.compile(user_query, re.IGNORECASE)
    results = list(movies_collection.find({"movie_name": {"$regex": query_regex}}))
    
    if results:
        status_msg = bot.send_message(chat_id, f"🎬 '{user_query.upper()}' ဖိုင်များကို ပို့ပေးနေပါတယ်...")
        for movie_data in results:
            movie_msg = bot.send_video(chat_id=chat_id, video=movie_data['file_id'], caption=f"🍿 **{movie_data['movie_name'].upper()}**")
            threading.Thread(target=auto_delete, args=(chat_id, movie_msg.message_id, DELETE_AFTER_SECONDS)).start()
        try:
            bot.delete_message(chat_id, status_msg.message_id)
        except:
            pass
    else:
        bot.send_message(chat_id, "❌ ရှာမတွေ့သေးပါဘူး။")

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    
    time.sleep(3) 
    
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBAPP_URL}/{BOT_TOKEN}")
    
    bot.run_webhooks(
        listen="0.0.0.0",
        port=port,
        url_path=BOT_TOKEN
    )
    
