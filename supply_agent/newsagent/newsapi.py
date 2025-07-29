import os
import sys
import requests
from newspaper import Article, ArticleException, Config
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

def get_full_article_text(url):
    """Verilen URL'den makalenin tam metnini güvenli bir şekilde çeker."""
    if not url:
        return None
    try:
        config = Config()
        config.browser_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        
        article_obj = Article(url, config=config, language='en')
        article_obj.download()
        article_obj.parse()
        return article_obj.text if article_obj.text else None
    except (ArticleException, ValueError):
        return None

def is_valid_article_text(text):
    if not text or len(text) < 300:  
        return False

    forbidden_words = ["log in", "login", "subscribe", "password", "user id", "create an account"]
    text_lower = text.lower()
    
    for word in forbidden_words:
        if word in text_lower:
            return False
            
    return True

def main():
    """Ana fonksiyon."""
    api_key = os.getenv("NEWS_API_KEY")
    if not api_key:
        print("HATA: NEWS_API_KEY ortam değişkeni bulunamadı.", file=sys.stderr)
        return

   
    risk_keywords = [
        "steel", "aluminum", "semiconductor", "chip", "lithium", "cobalt", "rubber",
        "logistics", "shipping", "port", "tariff", "strike", "disaster", "shortage","crisis","wars","harbour"
    ]
    context_keywords = ["automotive", "car manufacturing", "auto industry", "Ford"]
    query = f"(({' OR '.join(risk_keywords)}) AND ({' OR '.join(context_keywords)}))"

    
    two_days_ago = datetime.now() - timedelta(days=2)
    from_date = two_days_ago.strftime('%Y-%m-%d')

    url = f"https://newsapi.org/v2/everything?qInTitle={query}&language=en&from={from_date}&sortBy=publishedAt&pageSize=20&apiKey={api_key}"

    print(f"DEBUG: NewsAPI'ye gönderilen URL: {url}", file=sys.stderr)

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        articles = data.get("articles")
        article_count = len(articles) if articles else 0
        print(f"DEBUG: {article_count} adet potansiyel makale bulundu.", file=sys.stderr)

        if not articles:
            return

        valid_articles_texts = []
        for article_data in articles:
            if len(valid_articles_texts) >= 3:
                break

            article_url = article_data.get("url")
            print(f"DEBUG: Makale deneniyor: {article_url}", file=sys.stderr)
            
            full_text = get_full_article_text(article_url)
            
            if is_valid_article_text(full_text):
                print(f"DEBUG: Geçerli makale bulundu ve listeye eklendi: {article_url}", file=sys.stderr)
                valid_articles_texts.append(full_text)
            else:
                print(f"DEBUG: Makale geçerli değil (login/paywall olabilir), bir sonraki deneniyor...", file=sys.stderr)
        
        if valid_articles_texts:
            print("\n\n--- ARTICLE SEPARATOR ---\n\n".join(valid_articles_texts))
        else:
            print("DEBUG: Döngü sonunda hiç geçerli makale bulunamadı.", file=sys.stderr)


    except requests.exceptions.RequestException as e:
        print(f"Ağ hatası oluştu: {e}", file=sys.stderr)
    except requests.exceptions.JSONDecodeError:
        print("API'den gelen yanıt JSON formatında değil.", file=sys.stderr)

if __name__ == "__main__":
    main()
