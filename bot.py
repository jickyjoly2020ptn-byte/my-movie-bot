import telebot
import threading
from pymongo import MongoClient
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8660308040:AAFk1-p6xEjZ-PnELHnrI4s5LS3s0BNzllM"
bot = telebot.TeleBot(BOT_TOKEN)

MONGO_URI = "mongodb+srv://jickyjoly2020ptn_db_user:<Gjs8K6RcH8PASScG>@cluster0.uiuftrc.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['movie_bot_db']
series_collection = db['series_movies']

ADMIN_ID = 2043111276  # သင့် Telegram ID ထည့်ပါ

# ၁။ Admin က ဇာတ်လမ်းတွဲ အပိုင်းများကို Bot ထဲသို့ လှမ်းသိမ်းသည့်စနစ်
@bot.message_handler(content_types=['video', 'document'], func=lambda message: message.from_user.id == ADMIN_ID)
def save_series(message):
    file_id = message.video.file_id if message.content_type == 'video' else message.document.file_id
    sent_msg = bot.reply_to(message, "ဒီဖိုင်အတွက် ဒေတာကို `ဇာတ်လမ်းအမည်:အပိုင်းနာမည်` ပုံစံရိုက်ပေးပါ။\n(ဥပမာ - `breakingbad:ep1` သို့မဟုတ် `naruto:ep5`)")
    bot.register_next_step_handler(sent_msg, process_series_save, file_id)

def process_series_save(message, file_id):
    try:
        series_name, episode_name = message.text.strip().lower().split(':')
        
        # ဒေတာဘေ့စ်ထဲတွင် ဇာတ်လမ်းအမည်အောက်၌ အပိုင်းများကို စုစည်းသိမ်းဆည်းခြင်း
        series_collection.update_one(
            {"series_name": series_name},
            {"$set": {f"episodes.{episode_name}": file_id}},
            upsert=True
        )
        bot.reply_to(message, f"✅ သိမ်းဆည်းမှု အောင်မြင်ပါပြီ။\n\nChannel တွင် တင်ရမည့် လင့်ခ် -\n`https://t.me{bot.get_me().username}?start={series_name}`")
    except ValueError:
        bot.reply_to(message, "❌ ပုံစံမှားနေပါသည်။ `ဇာတ်လမ်းအမည်:အပိုင်းနာမည်` ပုံစံအတိုင်း ပြန်ပို့ပေးပါ။")

# ၂။ ဗီဒီယိုဖိုင်ကို ဖျက်ပြီး ခလုတ်ပြန်ပြောင်းပေးမည့် စနစ်
def auto_delete_and_replace(chat_id, message_id, series_name):
    try:
        bot.delete_message(chat_id, message_id)
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text="🔄 GET FILE AGAIN!", callback_data=f"list_{series_name}"))
        
        bot.send_message(
            chat_id, 
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ YOUR VIDEO / FILE IS SUCCESSFULLY DELETED !!\n\n"
            "ဗီဒီယိုဖိုင်ကို မူပိုင်ခွင့်အရ ဖြတ်တောက်ပစ်လိုက်ပါပြီ။\n"
            "ဇာတ်လမ်းတွဲ အပိုင်းများကို ပြန်ကြည့်ရန် အောက်က ခလုတ်ကို နှိပ်ပါ။\n"
            "━━━━━━━━━━━━━━━━━━━━━━", 
            reply_markup=markup
        )
    except Exception as e:
        print("Error in auto-delete:", e)

# ၃။ Channel ကလင့်ခ်ကို နှိပ်ပြီး ဝင်လာလျှင် Episode ခလုတ်အားလုံး ပြသပေးသည့်စနစ်
@bot.message_handler(commands=['start'])
def handle_start(message):
    args = message.text.split()
    if len(args) > 1:
        series_name = args[1].lower()
        show_episode_buttons(message.chat.id, series_name)
    else:
        bot.send_message(message.chat.id, "👋 မင်္ဂလာပါ။ ရုပ်ရှင်ကြည့်ရန် Channel ထဲက လင့်ခ်ကို နှိပ်ဝင်ပေးပါ။")

# အပိုင်းအားလုံးကို ခလုတ်ပြပေးမည့် Function
def show_episode_buttons(chat_id, series_name):
    series_data = series_collection.find_one({"series_name": series_name})
    
    if series_data and "episodes" in series_data:
        markup = InlineKeyboardMarkup()
        episodes = series_data["episodes"]
        
        # အပိုင်းများကို ခလုတ်များအဖြစ် ပြောင်းလဲခြင်း
        # (ဥပမာ ခလုတ်တစ်ခုကို နှိပ်လျှင် play_breakingbad_ep1 ဟု အလုပ်လုပ်မည်)
        for ep_name in sorted(episodes.keys()):
            btn = InlineKeyboardButton(text=f"🍿 {ep_name.upper()}", callback_data=f"play_{series_name}_{ep_name}")
            markup.add(btn)
            
        bot.send_message(chat_id, f"🎬 **{series_name.upper()}** ဇာတ်လမ်းတွဲ၏ ကြည့်ရှုလိုသော အပိုင်းကို ရွေးချယ်ပါ -", reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(chat_id, "❌ ဤဇာတ်လမ်းတွဲ သို့မဟုတ် အပိုင်းများကို ရှာမတွေ့သေးပါ။")

# ၄။ အသုံးပြုသူက Episode ခလုတ်တစ်ခုခုကို နှိပ်လိုက်လျှင် ဗီဒီယိုပို့ပေးပြီး Timer မောင်းနှင်ခြင်း
@bot.callback_query_handler(func=lambda call: call.data.startswith('play_'))
def callback_play_video(call):
    # data ပုံစံ - play_seriesname_epname
    _, series_name, ep_name = call.data.split('_')
    series_data = series_collection.find_one({"series_name": series_name})
    
    if series_data and ep_name in series_data["episodes"]:
        video_id = series_data["episodes"][ep_name]
        
        # ခလုတ်စာရင်းဟောင်းကို အရင်ဖျက်သည်
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        
        # ဗီဒီယိုပို့ပြီး ၅ မိနစ် (စက္ကန့် ၃၀၀) အကြာတွင် ဖျက်ရန် စီစဉ်ခြင်း
        sent_video = bot.send_video(call.message.chat.id, video_id, caption=f"🍿 {series_name.upper()} - {ep_name.upper()}\n\n⚠️ ဤဗီဒီယိုသည် ၅ မိနစ်အတွင်း အလိုအလျောက် ပျက်သွားပါမည်။")
        threading.Timer(300, auto_delete_and_replace, args=[call.message.chat.id, sent_video.message_id, series_name]).start()

# ၅။ "GET FILE AGAIN!" သို့မဟုတ် စာရင်းပြန်တောင်းလျှင် ခလုတ်များ ပြန်ပြပေးခြင်း
@bot.callback_query_handler(func=lambda call: call.data.startswith('list_'))
def callback_show_list_again(call):
    _, series_name = call.data.split('_')
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    show_episode_buttons(call.message.chat.id, series_name)

print("Series Movie Bot is running...")
bot.delete_webhook()
bot.polling(none_stop=True)
                            
