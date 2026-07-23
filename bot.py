import os
import telebot
import threading
import time
import re
from pymongo import MongoClient
import certifi

# === သတ်မှတ်ချက်များ တန်းထည့်ရန် ===
BOT_TOKEN = "8905382319:AAFraomykxkV6ChkIe_ad0IXuS-5ksYqrF4"  # သင့် Bot Token
WEBAPP_URL = "https://my-movie-bot-2-vsdp.onrender.com"  # သင့် Render Web URL
ADMIN_IDS = [2043111276]  # သင့် Telegram User ID (ဂဏန်းသက်သက်)
MONGO_URI = "mongodb+srv://botuser:<noVWoqQYdwDk5e4A>@cluster0.uiuftrc.mongodb.net/?appName=Cluster0"  # သင့် MongoDB URI

# ဗီဒီယို ပြန်ဖျက်ရန် အချိန် (စက္ကန့်ဖြင့်) - ၅ မိနစ် = ၃၀၀ စက္ကန့်
DELETE_AFTER_SECONDS = 300

# === စတင်ပြင်ဆင်ခြင်း ===
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
    except Exception as e:
        print(f"Error deleting message: {e}")

# /start Command
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "👋 မင်္ဂလာပါ! ရုပ်ရှင်နှင့် ဇာတ်လမ်းတွဲများ တောင်းနိုင်တဲ့ Bot ပါ။\n\n"
        "🔍 ဇာတ်လမ်းအမည်ကို ရိုက်ပြီး ရှာဖွေနိုင်ပါတယ်။\n"
        "ဥပမာ - 'Squid Game' ဟု ရိုက်ပါက အပိုင်းအားလုံး ကျလာပါမည်။\n\n"
        f"⚠️ သတိပေးချက် - ဗီဒီယိုဖိုင်များသည် **{int(DELETE_AFTER_SECONDS / 60)} မိနစ်** အတွင်း အလိုအလျောက် ပြန်ပျက်သွားပါမည်။"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

# === ADMIN စနစ် ===
@bot.message_handler(content_types=['video'], func=lambda message: message.from_user.id in ADMIN_IDS)
def add_movie_by_admin(message):
    if not message.caption:
        bot.reply_to(message, "❌ ကျေးဇူးပြု၍ ဗီဒီယို Caption တွင် ရုပ်ရှင်အမည် (သို့) Series အမည်နှင့် Ep ကို ထည့်ပေးပါ။")
        return
    
    movie_name = message.caption.lower().strip()
    file_id = message.video.file_id
    
    movies_collection.update_one(
        {"movie_name": movie_name},
        {"$set": {"file_id": file_id}},
        upsert=True
    )
    bot.reply_to(message, f"✅ **'{movie_name.upper()}'** ကို ထည့်သွင်းပြီးပါပြီ။")

# === USER စနစ် ===
@bot.message_handler(func=lambda message: True)
def search_and_send_movie(message):
    user_query = message.text.lower().strip()
    chat_id = message.chat.id
    
    # ရိုက်လိုက်တဲ့ နာမည်ပါဝင်တဲ့ ရလဒ်တွေအကုန်လုံး (All Episodes) ရှာခိုင်းခြင်း
    query_regex = re.compile(user_query, re.IGNORECASE)
    results = list(movies_collection.find({"movie_name": {"$regex": query_regex}}))
    
    if results:
        status_msg = bot.send_message(chat_id, f"🎬 '{user_query.upper()}' နှင့် ပတ်သက်သော ဖိုင်များကို ရှာတွေ့ပါပြီ။ Inbox သို့ ပို့ပေးနေပါတယ်...")
        
        # တွေ့သမျှ ဗီဒီယိုရလဒ်/အပိုင်း အားလုံးကို Loop ပတ်ပြီး ပို့ပေးခြင်း
        for movie_data in results:
            actual_name = movie_data['movie_name']
            file_id = movie_data['file_id']
            
            movie_msg = bot.send_video(
                chat_id=chat_id, 
                video=file_id, 
                caption=f"🍿 **{actual_name.upper()}**\n\n⚠️ ဤဗီဒီယိုသည် {int(DELETE_AFTER_SECONDS / 60)} မိနစ်အတွင်း ပျက်သွားပါမည်။"
            )
            
            # ဗီဒီယိုတစ်ခုချင်းစီကို အချိန်ပြည့်ရင် လိုက်ဖျက်ခိုင်းခြင်း
            threading.Thread(target=auto_delete, args=(chat_id, movie_msg.message_id, DELETE_AFTER_SECONDS)).start()
        
        # အကြောင်းကြားစာကို ပြန်ဖျက်ခြင်း
        try:
            bot.delete_message(chat_id, status_msg.message_id)
        except:
            pass
    else:
        bot.send_message(chat_id, "❌ သင်ရှာနေသော ရုပ်ရှင် (သို့) ဇာတ်လမ်းတွဲ အပိုင်းများကို ရှာမတွေ့သေးပါဘူး။")

# === Webhook စနစ်သတ်မှတ်ခြင်း ===
bot.remove_webhook()
bot.set_webhook(url=f"{WEBAPP_URL}/{BOT_TOKEN}")

if __name__ == "__main__":
    # Render အတွက် Port ချိတ်ဆက်ခြင်း (Error မတက်အောင် မဖြစ်မနေ လိုအပ်ပါသည်)
    port = int(os.environ.get('PORT', 5000))
    
    # Webhook Server ကို စတင်မောင်းနှင်ခြင်း
    bot.run_webhooks(
        listen="0.0.0.0",
        port=port,
        url_path=BOT_TOKEN
    )    welcome_text = (
        "👋 မင်္ဂလာပါ! ရုပ်ရှင်နှင့် ဇာတ်လမ်းတွဲများ တောင်းနိုင်တဲ့ Bot ပါ။\n\n"
        "🔍 ဇာတ်လမ်းအမည်ကို ရိုက်ပြီး ရှာဖွေနိုင်ပါတယ်။\n"
        "ဥပမာ - 'Squid Game' ဟု ရိုက်ပါက အပိုင်းအားလုံး ကျလာပါမည်။\n\n"
        f"⚠️ သတိပေးချက် - ဗီဒီယိုဖိုင်များသည် **{int(DELETE_AFTER_SECONDS / 60)} မိနစ်** အတွင်း အလိုအလျောက် ပြန်ပျက်သွားပါမည်။"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

# === ADMIN စနစ် ===
@bot.message_handler(content_types=['video'], func=lambda message: message.from_user.id in ADMIN_IDS)
def add_movie_by_admin(message):
    if not message.caption:
        bot.reply_to(message, "❌ ကျေးဇူးပြု၍ ဗီဒီယို Caption တွင် ရုပ်ရှင်အမည် (သို့) Series အမည်နှင့် Ep ကို ထည့်ပေးပါ။")
        return
    
    movie_name = message.caption.lower().strip()
    file_id = message.video.file_id
    
    movies_collection.update_one(
        {"movie_name": movie_name},
        {"$set": {"file_id": file_id}},
        upsert=True
    )
    bot.reply_to(message, f"✅ **'{movie_name.upper()}'** ကို ထည့်သွင်းပြီးပါပြီ။")

# === USER စနစ် ===
@bot.message_handler(func=lambda message: True)
def search_and_send_movie(message):
    user_query = message.text.lower().strip()
    chat_id = message.chat.id
    
    # ရိုက်လိုက်တဲ့ နာမည်ပါဝင်တဲ့ ရလဒ်တွေအကုန်လုံး (All Episodes) ရှာခိုင်းခြင်း
    query_regex = re.compile(user_query, re.IGNORECASE)
    results = list(movies_collection.find({"movie_name": {"$regex": query_regex}}))
    
    if results:
        status_msg = bot.send_message(chat_id, f"🎬 '{user_query.upper()}' နှင့် ပတ်သက်သော ဖိုင်များကို ရှာတွေ့ပါပြီ။ Inbox သို့ ပို့ပေးနေပါတယ်...")
        
        # တွေ့သမျှ ဗီဒီယိုရလဒ်/အပိုင်း အားလုံးကို Loop ပတ်ပြီး ပို့ပေးခြင်း
        for movie_data in results:
            actual_name = movie_data['movie_name']
            file_id = movie_data['file_id']
            
            movie_msg = bot.send_video(
                chat_id=chat_id, 
                video=file_id, 
                caption=f"🍿 **{actual_name.upper()}**\n\n⚠️ ဤဗီဒီယိုသည် {int(DELETE_AFTER_SECONDS / 60)} မိနစ်အတွင်း ပျက်သွားပါမည်။"
            )
            
            # ဗီဒီယိုတစ်ခုချင်းစီကို အချိန်ပြည့်ရင် လိုက်ဖျက်ခိုင်းခြင်း
            threading.Thread(target=auto_delete, args=(chat_id, movie_msg.message_id, DELETE_AFTER_SECONDS)).start()
        
        # အကြောင်းကြားစာကို ပြန်ဖျက်ခြင်း
        try:
            bot.delete_message(chat_id, status_msg.message_id)
        except:
            pass
    else:
        bot.send_message(chat_id, "❌ သင်ရှာနေသော ရုပ်ရှင် (သို့) ဇာတ်လမ်းတွဲ အပိုင်းများကို ရှာမတွေ့သေးပါဘူး။")

# === Webhook စနစ်သတ်မှတ်ခြင်း ===
bot.remove_webhook()
bot.set_webhook(url=f"{WEBAPP_URL}/{BOT_TOKEN}")

if __name__ == "__main__":
    # Render အတွက် Port ချိတ်ဆက်ခြင်း (Error မတက်အောင် မဖြစ်မနေ လိုအပ်ပါသည်)
    port = int(os.environ.get('PORT', 5000))
    
    # Webhook Server ကို စတင်မောင်းနှင်ခြင်း
    bot.run_webhooks(
        listen="0.0.0.0",
        port=port,
        url_path=BOT_TOKEN
    )
