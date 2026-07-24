import os
import telebot
import threading
import time
import re
import uuid
from pymongo import MongoClient
import certifi

# === အချက်အလက်များ တန်းထည့်ရန် ===
BOT_TOKEN = "8038762572:AAHl2CXYTiz58iMrEslIwOfJHhpoUCGlHgs" 
WEBAPP_URL = "https://onrender.com"  # သင့် Render URL အမှန်
ADMIN_IDS = [2043111276]  # သင့် Telegram User ID ဂဏန်း
MONGO_URI = "mongodb://botuser:jickymovie2026@ac-8w9cptn-shard-00-00.uluftrc.mongodb.net:27017,ac-8w9cptn-shard-00-01.uluftrc.mongodb.net:27017,ac-8w9cptn-shard-00-02.uluftrc.mongodb.net:27017/?ssl=true&replicaSet=atlas-m0wsp6-shard-00&authSource=admin&retryWrites=true&w=majority&appName=Cluster0"

DELETE_AFTER_SECONDS = 300 
bot = telebot.TeleBot(BOT_TOKEN)

client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client['telegram_movie_bot']
movies_collection = db['movies']

def auto_delete(chat_id, message_id, delay):
    time.sleep(delay)
    try: bot.delete_message(chat_id, message_id)
    except: pass

# === USER စနစ် ===
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    command_args = message.text.split()
    
    if len(command_args) > 1:
        search_key = command_args[1]
        
        direct_data = movies_collection.find_one({"movie_key": search_key})
        if direct_data:
            send_movie_file(chat_id, direct_data)
            return
            
        series_results = list(movies_collection.find({"series_key": search_key}).sort("episode_no", 1))
        if series_results:
            main_title = series_results[0]['movie_name'].upper()
            markup = telebot.types.InlineKeyboardMarkup()
            
            row = []
            for ep_data in series_results:
                btn = telebot.types.InlineKeyboardButton(text=f"🎞️ Ep {ep_data['episode_no']}", callback_data=f"ep_{ep_data['movie_key']}")
                row.append(btn)
                if len(row) == 2:
                    markup.row(*row)
                    row = []
            if row:
                markup.row(*row)
                
            bot.send_message(chat_id, f"🎬 **{main_title}**\n\n🍿 ကြည့်ရှုလိုသည့် အပိုင်းကို ရွေးချယ်နှိပ်ပါ -", reply_markup=markup, parse_mode="Markdown")
            return
            
        bot.send_message(chat_id, "❌ ဤဗီဒီယိုဖိုင်သည် သက်တမ်းကုန်ဆုံးသွားပြီ ဖြစ်ပါတယ်။")
        return

    welcome_text = (
        "👋 မင်္ဂလာပါ! ရုပ်ရှင်နှင့် ဇာတ်လမ်းတွဲများ သိမ်းဆည်းပေးတဲ့ Bot ပါ။\n\n"
        "📢 Channel ထဲက ရုပ်ရှင်လင့်ခ်များကို နှိပ်ပြီး ဤနေရာတွင် တိုက်ရိုက် ကြည့်ရှုနိုင်ပါတယ်။"
    )
    bot.send_message(chat_id, welcome_text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('ep_'))
def handle_episode_button(call):
    movie_key = call.data.split('_')[1]
    movie_data = movies_collection.find_one({"movie_key": movie_key})
    if movie_data:
        bot.answer_callback_query(call.id, text="ဗီဒီယို ပို့ပေးနေပါပြီ...")
        send_movie_file(call.message.chat.id, movie_data)
    else:
        bot.answer_callback_query(call.id, text="❌ ဖိုင်ရှာမတွေ့တော့ပါ။")

def send_movie_file(chat_id, movie_data):
    status_msg = bot.send_message(chat_id, "🍿 ဗီဒီယိုဖိုင်ကို ပို့ပေးနေပါတယ်...")
    caption_title = f"{movie_data['movie_name'].upper()}"
    if movie_data.get('is_series'):
        caption_title += f" - EP {movie_data['episode_no']}"
        
    movie_msg = bot.send_video(
        chat_id=chat_id, 
        video=movie_data['file_id'], 
        caption=f"🍿 **{caption_title}**\n\n⚠️ ဤဗီဒီယိုသည် {int(DELETE_AFTER_SECONDS / 60)} မိနစ်အတွင်း အလိုအလျောက် ပျက်သွားပါမည်။"
    )
    try: bot.delete_message(chat_id, status_msg.message_id)
    except: pass
    threading.Thread(target=auto_delete, args=(chat_id, movie_msg.message_id, DELETE_AFTER_SECONDS)).start()

# === ADMIN စနစ် ===
@bot.message_handler(content_types=['video'], func=lambda message: message.from_user.id in ADMIN_IDS)
def add_movie_by_video(message):
    file_id = message.video.file_id
    caption_text = message.caption if message.caption else "ရုပ်ရှင်အမည်မသိပါ"
    
    id_reply = (
        f"📋 **ဤဗီဒီယို၏ File ID စာသား-**\n\n`{file_id}`\n\n"
        f"💡 **အောက်ပါစာသားတစ်ခုလုံးကို လုံးဝ (လုံးဝ) ပြင်စရာမလိုဘဲ ကူးယူပြီး ဒီအတိုင်း တန်းပို့ပေးလိုက်ပါ-**\n\n"
        f"`add_mov: {file_id} | {caption_text}`"
    )
    bot.reply_to(message, id_reply, parse_mode="Markdown")

# Enter ခေါက်ပြီး စာကြောင်းအောက်ဆင်းသမျှ စာတန်းရှည်ကြီးတွေပါ အကုန်ဖတ်မည့်စနစ်
@bot.message_handler(func=lambda message: message.from_user.id in ADMIN_IDS and message.text.strip().startswith("add_mov:"))
def add_movie_by_text(message):
    try:
        clean_text = message.text.strip()[8:].strip()
        file_id, caption_text = clean_text.split("|", 1)
        process_and_save_movie(message, file_id.strip(), caption_text.strip())
    except:
        bot.reply_to(message, "❌ ပုံစံမှားနေပါသည်။ ရိုက်ရမည့်ပုံစံ 👉 `add_mov: File_ID | ကားနာမည်` ")

def process_and_save_movie(message, file_id, caption_text):
    movie_key = uuid.uuid4().hex[:8]
    bot_info = bot.get_me()
    raw_caption = caption_text.strip()
    
    match = re.search(r'(?:ep|episode)\s*(\d+)', raw_caption, re.IGNORECASE)
    
    if match:
        episode_no = int(match.group(1))
        series_name = re.sub(r'(?:ep|episode)\s*\d+', '', raw_caption, flags=re.IGNORECASE).strip().lower()
        
        existing_series = movies_collection.find_one({"movie_name": series_name, "is_series": True})
        series_key = existing_series['series_key'] if existing_series else uuid.uuid4().hex[:8]
        
        movies_collection.update_one(
            {"movie_name": series_name, "episode_no": episode_no},
            {"$set": {"file_id": file_id, "movie_key": movie_key, "series_key": series_key, "is_series": True, "episode_no": episode_no}},
            upsert=True
        )
        
        main_link = f"https://t.me{bot_info.username}?start={series_key}"
        ep_link = f"https://t.me{bot_info.username}?start={movie_key}"
        
        reply_text = (
            f"✅ **ဇာတ်လမ်းတွဲကို သိမ်းဆည်းပြီးပါပြီ။**\n\n"
            f"📺 ဇာတ်လမ်းတွဲအမည်: {series_name.upper()}\n"
            f"🎞️ အပိုင်းနံပါတ်: Ep {episode_no}\n\n"
            f"🔗 **Channel ခလုတ်တွင် ထည့်ရမည့် လင့်ခ်ချုပ် (Main Link):**\n`{main_link}`\n\n"
            f"🔗 **ဒီအပိုင်းတစ်ခုတည်း တန်းကြည့်စေချင်ရင် လင့်ခ်:**\n`{ep_link}`"
        )
    else:
        movie_name = raw_caption.lower()
        movies_collection.update_one(
            {"movie_name": movie_name},
            {"$set": {"file_id": file_id, "movie_key": movie_key, "is_series": False}},
            upsert=True
        )
        movie_link = f"https://t.me{bot_info.username}?start={movie_key}"
        
        reply_text = (
            f"✅ **ရုပ်ရှင် (Movie) ကို သိမ်းဆည်းပြီးပါပြီ။**\n\n"
            f"🎬 ရုပ်ရှင်အမည်: {movie_name.upper()}\n\n"
            f"🔗 **Channel ထဲတွင် ထည့်ရမည့် လင့်ခ်-**\n`{movie_link}`"
        )
    bot.send_message(message.chat.id, reply_text, parse_mode="Markdown")

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    
    # Render စမောင်းမောင်းချင်း Port Bind အရင်ပွင့်စေပြီးမှ ၃ စက္ကန့်ဆိုင်းကာ Webhook ချိတ်ဆက်သည့်စနစ် (429 အမှားကျော်ရန်)
    time.sleep(3)
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBAPP_URL}/{BOT_TOKEN}")
    
    bot.run_webhooks(listen="0.0.0.0", port=port, url_path=BOT_TOKEN)
        
