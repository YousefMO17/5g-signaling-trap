import json
from collections import Counter

def analyze_intel(log_file="signaling_intel.json"):
    try:
        with open(log_file, "r") as f:
            intel = json.load(f)
    except FileNotFoundError:
        print(f"[!] Error: {log_file} not found. Run the trap first to gather data.")
        return

    print("=" * 55)
    print("       5G SIGNALING THREAT INTELLIGENCE REPORT")
    print("=" * 55)
    
    # Total unique attackers
    print(f"\n[+] Total Unique Attackers : {len(intel)}")
    
    total_attempts = sum(v["attempt_count"] for v in intel.values())
    print(f"[+] Total Attack Attempts  : {total_attempts}")
    
    print("\n[📊] Attacker Classification by Activity:")
    print("-" * 40)
    
    # Sort from most active to least active
    sorted_attackers = sorted(
        intel.items(),
        key=lambda x: x[1]["attempt_count"],
        reverse=True
    )
    
    for ip, data in sorted_attackers:
        print(f"  {ip}")
        print(f"    ├── Attempts      : {data['attempt_count']}")
        print(f"    ├── First Seen    : {data['first_seen']}")
        
        # Attack types used by this specific IP
        attack_types = [m["message_type"] for m in data["messages"]]
        type_counts = Counter(attack_types)
        print(f"    └── Attack Types  :")
        for attack_type, count in type_counts.most_common():
            print(f"         • {attack_type}: {count} times")
    
    # Overall Most Common Commands (Global Stats)
    all_commands = []
    for data in intel.values():
        for msg in data["messages"]:
            all_commands.append(msg["message_type"])
    
    print("\n[🚨] Most Common Attack Types (Global):")
    print("-" * 40)
    for cmd, count in Counter(all_commands).most_common(5):
        print(f"  {count:3d}x  {cmd}")

if __name__ == "__main__":
    analyze_intel()