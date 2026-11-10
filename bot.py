import requests
import sqlite3
import math
import os
from telethon import TelegramClient, events, Button

# --- 1. المفاتيح من السيرفر فقط ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
ADMIN_ID = 7093374788  # الآي دي حقك - انت بس اللي تقدر تشحن
DEVELOPER_USERNAME = '@Aa151000'

SMS_API_KEY = os.getenv("KEY_5SIM")
SMS_BASE_URL = 'https://5sim.net/v1'
HEADERS = {'Authorization': f'Bearer {SMS_API_KEY}', 'Accept': 'application/json'}

bot = TelegramClient('custom_num_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# --- 2. قاعدة البيانات ---
conn = sqlite3.connect('global_users_wallet.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL)')
cursor.execute('''CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    user_id INTEGER,
    phone TEXT,
    country TEXT,
    product TEXT,
    real_price REAL,
    profit REAL,
    user_price REAL,
    status TEXT
)''')
conn.commit()

def get_balance(user_id):
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row: return row[0]
    cursor.execute("INSERT INTO users VALUES (?, ?)", (user_id, 0.0))
    conn.commit()
    return 0.0

def update_balance(user_id, amount):
    new_balance = get_balance(user_id) + amount
    cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
    conn.commit()
    return new_balance

# --- 3. معادلة الارباح ---
def calc_profit(real_price):
    if real_price <= 40:
        return 4.0
    else:
        return 2.0

def fetch_all_countries(product, sort_type="cheapest"):
    try:
        url = f"{SMS_BASE_URL}/guest/prices?product={product}"
        res = requests.get(url, headers=HEADERS, timeout=20).json()
        countries = []
        for country, operators in res.items():
            for operator, products in operators.items():
                if product in products:
                    info = products[product]
                    price = float(info.get('Price', 0))
                    count = int(info.get('Count', 0))
                    if count > 0:
                        profit = calc_profit(price)
                        user_price = price + profit
                        countries.append({
                            "country": country,
                            "operator": operator,
                            "price": user_price,
                            "real_price": price,
                            "profit": profit,
                            "count": count
                        })
        if sort_type == "cheapest":
            countries.sort(key=lambda x: x['price'])
        elif sort_type == "expensive":
            countries.sort(key=lambda x: x['price'], reverse=True)
        elif sort_type == "most":
            countries.sort(key=lambda x: x['count'], reverse=True)
        elif sort_type == "offers":
            countries = [c for c in countries if c['count'] >= 20]
            countries.sort(key=lambda x: x['price'])
            countries = countries[:15]
        return countries[:100]
    except Exception as e:
        print(f"Error: {e}")
        return []

def fetch_all_products():
    try:
        url = f"{SMS_BASE_URL}/guest/prices"
        res = requests.get(url, headers=HEADERS, timeout=20).json()
        s = set()
        for country, operators in res.items():
            for operator, products in operators.items():
                for prod, info in products.items():
                    if int(info.get('Count', 0)) > 0:
                        s.add(prod)
        return sorted(list(s))
    except:
        return ['whatsapp','telegram','google','facebook','instagram','tiktok']

# --- 4. اوامر الشحن - انت بس ---
@bot.on(events.NewMessage(pattern=r'/add (\d+) (\d+)'))
async def add_balance_cmd(event):
    if event.sender_id != ADMIN_ID:
        await event.respond("هذا الأمر للادمن فقط")
        return
    target_id = int(event.pattern_match.group(1))
    amount = float(event.pattern_match.group(2))
    new_bal = update_balance(target_id, amount)
    await event.respond(f"✅ تم شحن {amount:.1f} روبل للمستخدم `{target_id}`\nرصيده الحين: {new_bal:.1f} روبل")
    try:
        await bot.send_message(target_id, f"✅ تم شحن رصيدك بـ {amount:.1f} روبل\nرصيدك الحين: {new_bal:.1f} روبل\nتقدر تشتري الحين 👇")
    except:
        pass

@bot.on(events.NewMessage(pattern=r'/balance'))
async def my_balance_cmd(event):
    bal = get_balance(event.sender_id)
    await event.respond(f"رصيدك: {bal:.1f} روبل")

@bot.on(events.NewMessage(pattern=r'/myid'))
async def myid_cmd(event):
    await event.respond(f"الآي دي حقك: {event.sender_id}")

# --- 5. القائمة الرئيسية ---
@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    user_id = event.sender_id
    balance = get_balance(user_id)
    buttons = [
        [Button.inline("🔥 عروض واتساب", b"section_wa_offers")],
        [Button.inline("📈 الأكثر توفراً - واتساب", b"section_wa_most")],
        [Button.inline("💰 الأرخص - واتساب", b"section_wa_cheapest")],
        [Button.inline("💎 الأغلى - واتساب", b"section_wa_expensive")],
        [Button.inline("🔥 عروض تليجرام", b"section_tg_offers")],
        [Button.inline("📈 الأكثر توفراً - تليجرام", b"section_tg_most")],
        [Button.inline("💰 الأرخص - تليجرام", b"section_tg_cheapest")],
        [Button.inline("💎 الأغلى - تليجرام", b"section_tg_expensive")],
        [Button.inline("🌍 كل التطبيقات المتوفرة", b"section_all_apps")],
        [Button.inline("📦 طلباتي", b"my_orders")],
        [Button.inline("💳 شحن الرصيد", b"charge_wallet")],
        [Button.inline("👤 حسابي", b"my_account")]
    ]
    await event.respond(f"مرحبا بك! 👋\n\nرصيدك: {balance:.2f} روبل\nاختر القسم:", buttons=buttons)

@bot.on(events.CallbackQuery)
async def callback(event):
    user_id = event.sender_id
    data = event.data.decode('utf-8')

    if data == "back_to_start":
        await start(event)
        return
    if data == "my_account":
        balance = get_balance(user_id)
        cursor.execute("SELECT SUM(profit) FROM orders WHERE user_id=?", (user_id,))
        total_profit = cursor.fetchone()[0] or 0
        await event.edit(f"حسابك:\nID: {user_id}\nالرصيد: {balance:.2f} روبل\nإجمالي ربحك منك: {total_profit:.1f} روبل", buttons=[Button.inline("رجوع", b"back_to_start")])
        return
    if data == "my_orders":
        cursor.execute("SELECT order_id, phone, product, user_price, status FROM orders WHERE user_id=? ORDER BY rowid DESC LIMIT 10", (user_id,))
        rows = cursor.fetchall()
        if not rows:
            await event.edit("ما عندك طلبات بعد", buttons=[Button.inline("رجوع", b"back_to_start")])
            return
        txt = "📦 طلباتك الأخيرة:\n\n"
        buttons = []
        for oid, phone, prod, price, status in rows:
            txt += f"{prod} | {phone} | {price:.1f} روبل | {status}\n"
            buttons.append([Button.inline(f"الكود: {phone}", f"check_{oid}".encode())])
        buttons.append([Button.inline("رجوع", b"back_to_start")])
        await event.edit(txt, buttons=buttons)
        return
    if data == "charge_wallet":
        await event.edit(f"شحن الرصيد:\n\nحول الفلوس وبعدين ارسل الآي دي حقك هنا:\n`{user_id}`\n\nتواصل: {DEVELOPER_USERNAME}", buttons=[Button.inline("رجوع", b"back_to_start")])
        return
    if data == "section_all_apps":
        products = fetch_all_products()
        buttons = []
        for p in products[:20]:
            buttons.append([Button.inline(f"{p} ✅ متوفر", f"list_{p}_cheapest_0".encode())])
        buttons.append([Button.inline("رجوع", b"back_to_start")])
        await event.edit("🌍 كل التطبيقات اللي فيها أرقام متوفرة:", buttons=buttons)
        return
    if data.startswith("section_"):
        _, service, sort_type = data.split('_')
        product = 'telegram' if service == 'tg' else 'whatsapp'
        await show_list(event, service, product, sort_type, 0)
        return
    if data.startswith("list_"):
        _, product, sort_type, page = data.split('_')
        service = 'tg' if product == 'telegram' else 'wa'
        await show_list(event, service, product, sort_type, int(page))
        return

    if data.startswith("buy_"):
        _, service, country, operator, cost_str = data.split('_')
        cost = float(cost_str)
        product = 'telegram' if service == 'tg' else 'whatsapp'
        balance = get_balance(user_id)
        if balance < cost:
            await event.answer(f"رصيدك {balance:.1f} تحتاج {cost:.1f} - اشحن اول", alert=True)
            return
        await event.edit(f"⏳ حجز رقم {country}...")
        try:
            buy_url = f"{SMS_BASE_URL}/user/buy/activation/{country}/{operator}/{product}"
            r = requests.get(buy_url, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                await event.edit(f"❌ خطأ: {r.text[:200]}")
                return
            order_data = r.json()
            order_id = order_data.get('id')
            phone_number = order_data.get('phone')
            if not order_id:
                await event.edit("❌ نفدت الأرقام، اختر دولة ثانية")
                return
            if cost <= 44:
                profit = 4.0
                real_price = cost - 4.0
            else:
                profit = 2.0
                real_price = cost - 2.0
            new_balance = update_balance(user_id, -cost)
            cursor.execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?)", (str(order_id), user_id, phone_number, country, product, real_price, profit, cost, "WAITING"))
            conn.commit()
            await event.edit(
                f"✅ تم شراء الرقم!\n\n📱 الرقم: `{phone_number}`\n🌍 الدولة: {country}\n📦 التطبيق: {product}\n💰 تم خصم: {cost:.1f} روبل (شامل ربح {profit:.0f})\n💳 رصيدك الحين: {new_balance:.1f} روبل\n🆔 الطلب: {order_id}\n\nانتظر الكود...",
                buttons=[Button.inline("🔄 جلب الكود", f"check_{order_id}".encode()), Button.inline("القائمة", b"back_to_start")]
            )
        except Exception as e:
            await event.edit(f"❌ خطأ: {e}")
        return

    if data.startswith("check_"):
        order_id = data.split('_')[1]
        cursor.execute("SELECT phone, product, status FROM orders WHERE order_id=? AND user_id=?", (order_id, user_id))
        row = cursor.fetchone()
        if not row:
            await event.answer("هذا الطلب مو حقك", alert=True)
            return
        try:
            r = requests.get(f"{SMS_BASE_URL}/user/check/{order_id}", headers=HEADERS, timeout=15).json()
            if r.get('status') == 'RECEIVED':
                code = r.get('sms', [{}])[0].get('code', 'وصل')
                cursor.execute("UPDATE orders SET status='RECEIVED' WHERE order_id=?", (order_id,))
                conn.commit()
                await event.edit(f"✅ الكود وصل!\n\n📱 الرقم: {row[0]}\n🔑 الكود: `{code}`\n\nتم خصمه من رصيدك وقت الشراء، ما خصمنا شي الحين.", buttons=[Button.inline("رجوع", b"back_to_start")])
            elif r.get('status') == 'CANCELED':
                await event.edit("❌ الطلب ملغي")
            else:
                await event.answer("لسا ما وصل الكود، انتظر شوي واضغط مرة ثانية", alert=True)
        except Exception as e:
            await event.answer(f"خطأ: {e}", alert=True)
        return

async def show_list(event, service, product, sort_type, page):
    titles = {"offers": "🔥 العروض", "most": "📈 الأكثر توفراً", "cheapest": "💰 الأرخص", "expensive": "💎 الأغلى"}
    await event.edit(f"⏳ جاري جلب الدول...")
    all_countries = fetch_all_countries(product, sort_type)
    if not all_countries:
        await event.edit("❌ تأكد من المفاتيح في السيرفر", buttons=[Button.inline("رجوع", b"back_to_start")])
        return
    items_per_page = 6
    total_pages = math.ceil(len(all_countries) / items_per_page)
    start_idx = page * items_per_page
    current_page = all_countries[start_idx:start_idx+items_per_page]
    buttons = []
    for c in current_page:
        btn_text = f"{c['country']} | {c['price']:.1f} روبل (ربح {c['profit']:.0f}) | متوفر: {c['count']}"
        buttons.append([Button.inline(btn_text, f"buy_{service}_{c['country']}_{c['operator']}_{c['price']}".encode())])
    nav_buttons = []
    if page > 0:
        nav_buttons.append(Button.inline("السابق", f"list_{product}_{sort_type}_{page-1}".encode()))
    if page < total_pages - 1:
        nav_buttons.append(Button.inline("التالي", f"list_{product}_{sort_type}_{page+1}".encode()))
    if nav_buttons:
        buttons.append(nav_buttons)
    buttons.append([Button.inline("القائمة الرئيسية", b"back_to_start")])
    await event.edit(titles.get(sort_type, "قائمة الدول"), buttons=buttons)

bot.run_until_disconnected()
