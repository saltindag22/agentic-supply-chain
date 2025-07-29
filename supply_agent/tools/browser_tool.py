import subprocess
import sys
import os

def run_browser_agent(search_prompt: str):
    """
    browser_use/main.py script'ini bir komut satırı argümanı (search_prompt) ile
    çalıştırır ve çıktısını döndürür.
    """
    print("--- Çalıştırılıyor: Browser Agent ---")
    
    script_path = os.path.join('browser_agent', 'browser.py')
    
    try:
        result = subprocess.run(
            [sys.executable, script_path, search_prompt],
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
