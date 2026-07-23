import os
import telebot
import threading
import time
import re
from pymongo import MongoClient
import certifi

# === သတ်မှတ်ချက်များ ထည့်ရန် ===
BOT_TOKEN = "8959345427:AAGjpb-AHuY_XCyyXkiCJnZkrorSybAvzEo"
# ဥပမာ - [12345678, 98765432] (သင့် Telegram User ID ကို ထည့်ပါ၊ တစ်ဦးထက်ပို၍ ထည့်နိုင်သည်)
ADMIN_IDS = [2043111276] 

# MongoDB Connection String (ဥပမာ - mongodb+srv://...)
MONGO_URI = "mongodb+srv://botuser:<noVWoqQYdwDk5e4A>@cluster0.uiuftrc.mongodb.net/?appName=Cluster0"

# ဗီဒီယို ပြန်ဖျက်ရန် အချိန် (စက္ကန့်ဖြင့်) - ၅ မိနစ် = ၃၀၀ စက္ကန့်
DELETE_AFTER_SECONDS = 300

# === ပြင်ဆင်မှုများ စတင်ခြင်း ===
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
        "🔍 ရုပ်ရှင်အမည်ကို အင်္ဂလိပ်လို (သို့မဟုတ်) စာလုံးအချို့ ရိုက်ပြီး ရှာဖွေနိုင်ပါတယ်။\n"
        f"⚠️ သတိပေးချက် - မူပိုင်ခွင့်ကြောင့် ပို့ပေးတဲ့ ဗီဒီယိုဖိုင်ဟာ **{int(DELETE_AFTER_SECONDS / 60)} မိနစ်** အတွင်း အလိုအလျောက် ပြန်ပျက်သွားပါမယ်။"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

# === ADMIN စနစ် - ရုပ်ရှင်အသစ် သိမ်းဆည်းခြင်း ===
# Admin က ဗီဒီယိုကို Caption ထည့်ပြီး ပို့လိုက်လျှင် Database ထဲသို့ တန်းသိမ်းမည်။
@bot.message_handler(content_types=['video'], func=lambda message: message.from_user.id in ADMIN_IDS)
def add_movie_by_admin(message):
    if not message.caption:
        bot.reply_to(message, "❌ ကျေးဇူးပြု၍ ဗီဒီယို ပို့သည့်အခါ Caption တွင် ရုပ်ရှင်အမည်ကိုပါ တစ်ခါတည်း ရိုက်ထည့်ပေးပါ။")
        return
    
    movie_name = message.caption.lower().strip()
    file_id = message.video.file_id
    
    # MongoDB ထဲတွင် အဟောင်းရှိမရှိစစ်ပြီး အသစ်ထည့်/မွမ်းမံခြင်း
    movies_collection.update_one(
        {"movie_name": movie_name},
        {"$set": {"file_id": file_id}},
        upsert=True
    )
    bot.reply_to(message, f"✅ ရုပ်ရှင် **'{movie_name.upper()}'** ကို Database ထဲသို့ အောင်မြင်စွာ ထည့်သွင်းပြီးပါပြီ။")

# === USER စနစ် - စာရိုက်၍ ရုပ်ရှင်ရှာဖွေခြင်း ===
@bot.message_handler(func=lambda message: True)
def search_and_send_movie(message):
    user_query = message.text.lower().strip()
    chat_id = message.chat.id
    
    # စာလုံးအချို့ ပါဝင်ရုံဖြင့် ရှာဖွေနိုင်ရန် Regex သုံးခြင်း
    # ဥပမာ - "spider" ဟု ရိုက်လျှင် "spider-man 1", "the amazing spider-man" အကုန်ထွက်လာမည်။
    query_regex = re.compile(user_query, re.IGNORECASE)
    results = list(movies_collection.find({"movie_name": {"$regex": query_regex}}))
    
    if results:
        # ရှာဖွေမှု အဆင်ပြေစေရန် ပထမဆုံးတွေ့သော ရလဒ်ကို အရင်ပို့ပေးခြင်း
        # (ရလဒ်များစွာ ပြလိုပါက List အနေဖြင့် ပြုပြင်နိုင်သည်)
        movie_data = results[0]
        actual_name = movie_data['movie_name']
        file_id = movie_data['file_id']
        
        status_msg = bot.send_message(chat_id, f"🎬 '{actual_name.upper()}' ကို ရှာတွေ့ပါပြီ။ Inbox သို့ ပို့ပေးနေပါတယ်...")
        
        movie_msg = bot.send_video(
            chat_id=chat_id, 
            video=file_id, 
            caption=f"🍿 **{actual_name.upper()}**\n\n⚠️ ဤဗီဒီယိုသည် {int(DELETE_AFTER_SECONDS / 60)} မိနစ်အတွင်း အလိုအလျောက် ပျက်သွားပါမည်။"
        )
        
        try:
            bot.delete_message(chat_id, status_msg.message_id)
        except:
            pass
            
        # အချိန်ပြည့်လျှင် ဗီဒီယိုဖိုင်ကို ပြန်ဖျက်ရန် Thread စတင်ခြင်း
        threading.Thread(target=auto_delete, args=(chat_id, movie_msg.message_id, DELETE_AFTER_SECONDS)).start()
        
    else:
        bot.send_message(chat_id, "❌ စိတ်မရှိပါနဲ့၊ သင်တောင်းဆိုတဲ့ ရုပ်ရှင်ကို စာရင်းထဲမှာ ရှာမတွေ့သေးပါဘူး။")

@bot.message_handler(content_types=['video'])
def get_file_id(message):
    print("Video File ID is:", message.video.file_id)
        
if __name__ == "__main__":
    print("Bot is running with MongoDB...")
    bot.infinity_polling()

    
