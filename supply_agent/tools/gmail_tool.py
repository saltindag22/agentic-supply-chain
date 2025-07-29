import subprocess
import sys
import os

def run_email_agent():
    """
    gmail_agent/send_initial_emails.py script'ini çalıştırır ve parser'dan gelen
    JSON verisini standart input (stdin) üzerinden bu script'e gönderir.
    """
    print("--- Çalıştırılıyor: Email Agent (İlk Temas) ---")
    
    script_path = os.path.join('gmail_agent', 'send_initial_emails.py')

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8'
        )
        return result.stdout.strip()
        
    except subprocess.CalledProcessError as e:
        print(f"HATA: {script_path} çalıştırılırken bir hata oluştu.")
        print(f"Hata Detayları:\n{e.stderr}")
        return None
    except FileNotFoundError:
        print(f"HATA: {script_path} dosyası bulunamadı.")
        return None
