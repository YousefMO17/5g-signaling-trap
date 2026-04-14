import socket, threading, time, json, hashlib
from datetime import datetime

TRAP_HOST = "0.0.0.0"
TRAP_PORT = 3868          # Standard DIAMETER Port
LOG_FILE = "signaling_intel.json"

attacker_intel = {}

def log_threat(attacker_ip, message_type, raw_data):
    timestamp = datetime.now().isoformat()
    
    fingerprint = hashlib.sha256(
        f"{attacker_ip}{raw_data[:50]}".encode()
    ).hexdigest()[:16]
    
    intel_entry = {
        "timestamp": timestamp,
        "attacker_ip": attacker_ip,
        "fingerprint": fingerprint,
        "message_type": message_type,
        "data_preview": raw_data[:100].hex(),
        "attack_vector": "SS7/DIAMETER_ABUSE"
    }
    
    if attacker_ip not in attacker_intel:
        attacker_intel[attacker_ip] = {
            "first_seen": timestamp,
            "attempt_count": 0,
            "messages": []
        }
    
    attacker_intel[attacker_ip]["attempt_count"] += 1
    attacker_intel[attacker_ip]["messages"].append(intel_entry)
    
    with open(LOG_FILE, "w") as f:
        json.dump(attacker_intel, f, indent=2)
    
    print(f"[🎯 INTEL] Attacker: {attacker_ip} | Type: {message_type} | #{attacker_intel[attacker_ip]['attempt_count']}")
    
    return fingerprint

def craft_fake_diameter_response(request_type):
    """
    رد وهمي بـ DIAMETER Protocol
    بيخلي المهاجم يفتكر إنه بيكلم Server حقيقي
    
    DIAMETER Header Structure:
    [Version(1)] [Length(3)] [Flags(1)] [Command-Code(3)] [App-ID(4)] [Hop-ID(4)] [End-ID(4)]
    """
    fake_response = bytearray([
        0x01,           # Version = 1
        0x00, 0x00, 0x14,  # Message Length = 20 bytes
        0x00,           # Flags (No Request bit)
        0x00, 0x01, 0x01,  # Command Code: Capabilities-Exchange-Answer
        0x00, 0x00, 0x00, 0x00,  # Application-ID
        0xFF, 0xFF, 0xFF, 0xFF,  # Hop-by-Hop ID (random)
        0xDE, 0xAD, 0xBE, 0xEF,  # End-to-End ID (fake)
    ])
    return bytes(fake_response)

def tarpit_attacker(conn, attacker_ip, duration=45):
    """
    Tarpit: إبقاء المهاجم معلق لمدة 45 ثانية
    بيبعتله بيانات بطيئة عشان يضيع وقته ومواردة
    """
    print(f"[🕸️  TARPIT] Engaging attacker {attacker_ip} for {duration}s...")
    
    start_time = time.time()
    fake_data_chunks = [
        b"\x01\x00\x00\x28",  
        b"\x00\x00\x01",        
        b"\x10\x00\x00",
    ]
    
    chunk_idx = 0
    while time.time() - start_time < duration:
        try:
            conn.send(fake_data_chunks[chunk_idx % len(fake_data_chunks)])
            chunk_idx += 1
            time.sleep(3)  
        except:
            break
    
    print(f"[🕸️  TARPIT] Released attacker {attacker_ip} after {duration}s")

def handle_attacker(conn, addr):
    """معالجة كل اتصال مشبوه"""
    attacker_ip = addr[0]
    
    print(f"\n[⚠️  CONTACT] Signaling probe from: {attacker_ip}:{addr[1]}")
    
    try:
        raw_data = conn.recv(4096)
        
        if not raw_data:
            return
        
       
        if len(raw_data) >= 8:
            command_code = int.from_bytes(raw_data[5:8], 'big')
            
            message_types = {
                257: "Capabilities-Exchange-Request (CER)",   # محاولة اتصال
                265: "AA-Request - Auth Probe",               # محاولة Auth
                272: "Credit-Control-Request",                # محاولة سرقة بيانات Billing
                280: "Device-Watchdog-Request",               # Scanning
                282: "Disconnect-Peer-Request",               # محاولة قطع
            }
            
            msg_type = message_types.get(command_code, f"Unknown-Command-{command_code}")
        else:
            msg_type = "Malformed/Custom-Probe"
        
        # سجل التهديد
        fingerprint = log_threat(attacker_ip, msg_type, raw_data)
        
        print(f"[🔎 ANALYSIS] Command: {msg_type} | Fingerprint: {fingerprint}")
        
        fake_response = craft_fake_diameter_response(msg_type)
        conn.send(fake_response)
        
        if "Auth" in msg_type or "Credit" in msg_type:
            print(f"[🚨 HIGH PRIORITY] Aggressive probe detected - Deploying TARPIT")
            tarpit_thread = threading.Thread(
                target=tarpit_attacker, 
                args=(conn, attacker_ip, 60)
            )
            tarpit_thread.start()
            tarpit_thread.join()
        else:
            tarpit_attacker(conn, attacker_ip, 15)
            
    except Exception as e:
        print(f"[ERROR] Handler error for {attacker_ip}: {e}")
    finally:
        conn.close()
        print(f"[🔒] Connection closed: {attacker_ip}")


def start_signaling_trap():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((TRAP_HOST, TRAP_PORT))
    server.listen(50)
    
    print(f"""
╔══════════════════════════════════════════╗
║   5G SIGNALING TRAP - DIAMETER HONEYPOT  ║
║   Listening on Port {TRAP_PORT}(DIAMETER)║ 
║   Threat Intel → {LOG_FILE}              ║
╚══════════════════════════════════════════╝
    """)
    
    while True:
        conn, addr = server.accept()
        t = threading.Thread(target=handle_attacker, args=(conn, addr))
        t.daemon = True
        t.start()

start_signaling_trap()