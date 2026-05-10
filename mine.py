import telebot
from telebot import types
import json
import os
import random
import threading
import time
from datetime import datetime, timedelta

# --- الإعدادات الأساسية ---
API_TOKEN = '8620272453:AAEDxKhjR3959qmnzChH6oJXM5gYQLuLK1M'
bot = telebot.TeleBot(API_TOKEN)

DB_FILE = 'database.json'
OWNER_ID = 1 

# --- الأسعار والمحرك (مثل الصور اللي دزيتها) ---
STOCKS = {
    "Apple 🍎": {"price": 150.0},
    "Tesla ⚡": {"price": 1000.0},
    "Bitcoin ₿": {"price": 1000000.0}
}

ESTATES = {
    "مطعم 🍔": {"price": 1000000, "daily": 50000},
    "فندق 🏨": {"price": 2000000, "daily": 150000},
    "ملعب 🏟️": {"price": 5000000, "daily": 350000},
    "برج 🗼": {"price": 100000000, "daily": 500000}
}

# --- محرك السوق الاحترافي (تحديث كل 2 ثانية) ---
def market_engine():
    while True:
        for stock in STOCKS:
            old_price = STOCKS[stock]["price"]
            change = random.uniform(-0.04, 0.04) # حركة طبيعية
            
            if random.random() < 0.07: # صعود قوي
                change += random.uniform(0.10, 0.35)
            if random.random() < 0.07: # نزول قوي
                change -= random.uniform(0.10, 0.30)
            
            new_price = old_price * (1 + change)
            
            # حماية الانهيار (برمجتك يا بطل)
            if stock == "Bitcoin ₿": new_price = max(100000, new_price)
            elif stock == "Tesla ⚡": new_price = max(100, new_price)
            elif stock == "Apple 🍎": new_price = max(50, new_price)
            
            STOCKS[stock]["price"] = round(new_price, 2)
        time.sleep(2)

threading.Thread(target=market_engine, daemon=True).start()

# --- نظام البيانات ---
def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_data():
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

users = load_data()

# --- القائمة الرئيسية ---
def main_markup(cid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('📄 كشف حساب', '💹 تداول')
    markup.add('🏠 عقارات', '💵 سحب الأرباح')
    markup.add('💸 تحويل فلوس') # الزر الجديد
    if users.get(cid, {}).get('id') == OWNER_ID:
        markup.add('⚙️ لوحة المالك')
    return markup

# --- الأوامر ---
@bot.message_handler(commands=['start'])
def start(message):
    cid = str(message.chat.id)
    if cid not in users:
        users[cid] = {
            'id': len(users) + 1, 'balance': 50000, 'name': message.from_user.first_name,
            'portfolio': {n: 0 for n in STOCKS}, 'estates': {n: 0 for n in ESTATES},
            'last_claim': None
        }
        save_data()
    bot.send_message(cid, f"أهلاً بك {users[cid]['name']}! تم تشغيل النظام.", reply_markup=main_markup(cid))

@bot.message_handler(func=lambda m: m.text == '📄 كشف حساب')
def info(message):
    cid = str(message.chat.id)
    u = users[cid]
    total_players = len(users) # عدد اللاعبين الكلي
    est = "\n".join([f"- {k}: {v}" for k, v in u['estates'].items() if v > 0])
    msg = (f"📊 إحصائيات النظام:\n👥 عدد اللاعبين: {total_players}\n━━━━━━━━━━━━\n"
           f"👤 الاسم: {u['name']}\n🔢 الـ ID الخاص بك: {u['id']}\n💰 الرصيد: {u['balance']:,}$\n"
           f"🏠 عقاراتك: \n{est if est else 'لا توجد'}")
    bot.reply_to(message, msg)

@bot.message_handler(func=lambda m: m.text == '💹 تداول')
def trade(message):
    markup = types.InlineKeyboardMarkup()
    for s in STOCKS:
        p = STOCKS[s]['price']
        markup.add(
            types.InlineKeyboardButton(f"📈 شراء {s} | {p}$", callback_data=f"buy_{s}"),
            types.InlineKeyboardButton(f"📉 بيع {s} | {p}$", callback_data=f"sell_{s}")
        )
    bot.send_message(message.chat.id, "💹 سوق التداول المباشر:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith(('buy_', 'sell_')))
def handle_trade(call):
    cid = str(call.message.chat.id)
    action, name = call.data.split('_')
    price = STOCKS[name]['price']
    if action == 'buy' and users[cid]['balance'] >= price:
        users[cid]['balance'] -= price
        users[cid]['portfolio'][name] = users[cid]['portfolio'].get(name, 0) + 1
        save_data()
        bot.answer_callback_query(call.id, f"✅ تم شراء {name}")
    elif action == 'sell' and users[cid]['portfolio'].get(name, 0) > 0:
        users[cid]['balance'] += price
        users[cid]['portfolio'][name] -= 1
        save_data()
        bot.answer_callback_query(call.id, f"💰 تم بيع {name}")
    else: bot.answer_callback_query(call.id, "فشلت العملية!", show_alert=True)

# --- نظام تحويل الفلوس (الطلب الجديد) ---
@bot.message_handler(func=lambda m: m.text == '💸 تحويل فلوس')
def transfer_start(message):
    msg = bot.send_message(message.chat.id, "أرسل (ID الشخص) ثم (المبلغ)\nمثال: 5 1000")
    bot.register_next_step_handler(msg, transfer_process)

def transfer_process(message):
    try:
        cid = str(message.chat.id)
        target_id, amount = map(int, message.text.split())
        
        if amount <= 0:
            bot.reply_to(message, "المبلغ لازم يكون أكثر من 0!")
            return
            
        if users[cid]['balance'] < amount:
            bot.reply_to(message, "رصيدك ما يكفي!")
            return
            
        # البحث عن الشخص المطلوب بالـ ID
        target_cid = next((k for k, v in users.items() if v['id'] == target_id), None)
        
        if target_cid:
            if target_cid == cid:
                bot.reply_to(message, "ما يصير تحول لنفسك!")
                return
                
            users[cid]['balance'] -= amount
            users[target_cid]['balance'] += amount
            save_data()
            bot.reply_to(message, f"✅ تم تحويل {amount}$ إلى {users[target_cid]['name']} بنجاح!")
            bot.send_message(target_cid, f"💰 وصلك مبلغ {amount}$ من اللاعب {users[cid]['name']}!")
        else:
            bot.reply_to(message, "هذا الـ ID غير موجود!")
    except:
        bot.reply_to(message, "خطأ في التنسيق! أرسل رقمين فقط (ID ومبلغ).")

# --- العقارات وأرباحها ---
@bot.message_handler(func=lambda m: m.text == '🏠 عقارات')
def estates_menu(message):
    markup = types.InlineKeyboardMarkup()
    for n, v in ESTATES.items():
        markup.add(types.InlineKeyboardButton(f"شراء {n} | {v['price']:,}$", callback_data=f"best_{n}"))
    bot.send_message(message.chat.id, "🏠 سوق العقارات:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('best_'))
def buy_estate(call):
    cid = str(call.message.chat.id)
    name = call.data.split('_')[1]
    price = ESTATES[name]['price']
    if users[cid]['balance'] >= price:
        users[cid]['balance'] -= price
        users[cid]['estates'][name] += 1
        save_data()
        bot.answer_callback_query(call.id, f"مبروك شراء {name}! ✅")
    else: bot.answer_callback_query(call.id, "رصيدك ناقص!", show_alert=True)

@bot.message_handler(func=lambda m: m.text == '💵 سحب الأرباح')
def claim(message):
    u = users[str(message.chat.id)]
    total = sum(u['estates'][n] * ESTATES[n]['daily'] for n in ESTATES)
    if total > 0:
        u['balance'] += total
        save_data()
        bot.reply_to(message, f"💰 استلمت {total:,}$ من عقاراتك!")
    else: bot.reply_to(message, "ما عندك عقارات!")

# --- لوحة المالك (إضافة مبالغ) ---
@bot.message_handler(func=lambda m: m.text == '⚙️ لوحة المالك')
def admin(message):
    if users.get(str(message.chat.id), {}).get('id') == OWNER_ID:
        msg = bot.send_message(message.chat.id, "لوحة المالك: أرسل ID المبلغ")
        bot.register_next_step_handler(msg, admin_do)

def admin_do(message):
    try:
        pid, amt = map(int, message.text.split())
        t_cid = next((k for k, v in users.items() if v['id'] == pid), None)
        if t_cid:
            users[t_cid]['balance'] += amt
            save_data()
            bot.reply_to(message, "تمت الإضافة ✅")
    except: bot.reply_to(message, "خطأ!")

print("تم دمج كل شيء.. البوت جاهز 🔥")
bot.polling(none_stop=True)
