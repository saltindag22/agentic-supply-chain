import subprocess
import sys
import os

def run_news_agent():
    """
    news_api/main.py script'ini çalıştırır ve standart çıktısını (stdout) döndürür.
    Bu, LangGraph'ın news_agent'ı bir araç olarak kullanmasını sağlar.
    """
    print("--- Çalıştırılıyor: News Agent ---")
    
    
    script_path = os.path.join('newsagent', 'newsapi.py')
    
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
        
        print(f"HATA: {script_path} dosyası bulunamadı. Dosya yapınızı kontrol edin.")
        return None