import json
import os
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from pymongo import MongoClient


load_dotenv() 

from tools.news_tool import run_news_agent
from tools.browser_tool import run_browser_agent
from tools.gmail_tool import run_email_agent


class WorkflowState(TypedDict):
    news_articles: str
    search_prompt: str
    browser_output: str
    suppliers_json: str
    db_status: str
    final_status: str



def news_node(state: WorkflowState):
    """Haberleri çeken news_agent'ı çalıştırır."""
    print("--- Düğüm 1: Haberler Çekiliyor... ---")
    content = run_news_agent()
    if not content:
        raise ValueError("Haber agent'ı içerik döndüremedi. Akış durduruluyor.")
    return {"news_articles": content}

def risk_analyst_node(state: WorkflowState):
    """Haberleri analiz eder ve browser_agent için bir arama sorgusu (prompt) üretir."""
    print("--- Düğüm 2: Risk Analizi Yapılıyor... ---")
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro-latest", temperature=0)
    
    prompt_template = f"""
    You are a senior supply chain risk analyst for Ford Otosan. Analyze the following news articles, 
    separated by '--- ARTICLE SEPARATOR ---', and identify the SINGLE MOST CRITICAL supply chain risk. 

    Based on this risk, generate a **web search prompt** that follows this pattern exactly:
    "Find 3 company name and contact email for suppliers of <material/service>: 
    {{company_name: ..., email: ...}}"

    Replace <material/service> with the specific item or service affected by the risk. Your goal is to search 
    for **alternative suppliers** to mitigate the identified risk.

    Return your response ONLY as a JSON object in the following format:
    {{
    "search_prompt": "<your search prompt here>"
    }}

    News Articles:
    {state['news_articles']}
    """

    
    response = llm.invoke(prompt_template)
    clean_response = response.content.strip().replace("```json", "").replace("```", "")
    analysis = json.loads(clean_response)
    print(f"Risk analizi tamamlandı. Yeni arama sorgusu: {analysis['search_prompt']}")
    return {"search_prompt": analysis['search_prompt']}

def browser_node(state: WorkflowState):
    """Web'de araştırma yapan browser_agent'ı çalıştırır."""
    print("--- Düğüm 3: Web'de Araştırma Yapılıyor... ---")
    output = run_browser_agent(state['search_prompt'])
    if not output:
        raise ValueError("Browser agent'ı sonuç döndüremedi. Akış durduruluyor.")
    return {"browser_output": output}



import json
import re

def is_valid_email(email: str) -> bool:
    """Basit bir regex ile email formatını doğrular."""
    email_regex = r"^[\w\.-]+@[\w\.-]+\.\w{2,}$"
    return re.match(email_regex, email) is not None

def parser_node(state: WorkflowState):
    """Browser agent'ın ham çıktısını analiz edip temiz bir JSON'a dönüştürür."""
    print("--- Düğüm 4: Araştırma Sonuçları Ayıklanıyor... ---")
    llm = ChatGoogleGenerativeAI(model="models/gemini-1.5-flash-latest", temperature=0)
    
    prompt_template = f"""
    Analyze the text below which contains information about potential suppliers.
    For each supplier found in the text, extract the company name, their contact email,
    and the specific product or service that is mentioned in the context of that company.

    Provide your response as a JSON formatted list of objects. Each object must contain
    "company_name", "email", and "product_name" keys.

    Example format: 
    [{{"company_name": "Example Steel Corp.", "email": "contact@examplesteel.com", "product_name": "High-strength steel plates"}}, ...]

    Text:
    {state['browser_output']}
    """
    response = llm.invoke(prompt_template)

    if isinstance(response.content, list):
        raw_text = " ".join(response.content)
    else:
        raw_text = response.content

    raw_output = raw_text.strip().replace("```json", "").replace("```", "")

    try:
        parsed_list = json.loads(raw_output)
        filtered_list = [
            item for item in parsed_list
            if item.get("email") and item["email"].strip() != "" and is_valid_email(item["email"].strip())
        ]
    except json.JSONDecodeError as e:
        print(f"❌ JSON parse hatası: {e}")
        filtered_list = []

    print(f"Ayıklanan Tedarikçiler (Geçerli Email ile Filtrelenmiş JSON): {json.dumps(filtered_list, indent=2)}")
    return {"suppliers_json": filtered_list}

def save_to_db_node(state: WorkflowState):
    """Parser'dan gelen JSON verisini MongoDB'ye kaydeder."""
    print("--- Ara Katman: Veritabanına Kaydediliyor... ---")
    
    mongo_uri = os.getenv("MONGO_URI")
    db_name = os.getenv("DB_NAME", "ai_agent_db")
    collection_name = "mailing_list" # Hedef koleksiyon
    
    if not mongo_uri:
        raise ValueError("MONGO_URI ortam değişkeni .env dosyasında bulunamadı.")
        
    try:
        client = MongoClient(mongo_uri)
        db = client[db_name]
        collection = db[collection_name]
        
        suppliers = state['suppliers_json']
        
        if not suppliers:
            status_message = "Ayıklanan tedarikçi listesi boş. Veritabanına kayıt yapılmadı."
            print(status_message)
            return {"db_status": status_message}

        for supplier in suppliers:
            supplier['status'] = 'pending'
            
        result = collection.insert_many(suppliers)
        status_message = f"{len(result.inserted_ids)} adet yeni tedarikçi veritabanına eklendi."
        print(status_message)
        return {"db_status": status_message}

    except Exception as e:
        error_message = f"Veritabanına kaydederken hata oluştu: {e}"
        print(error_message)
        raise e

def email_agent_node(state: WorkflowState):
    """Veritabanındaki yeni tedarikçilere ilk e-postayı gönderen agent'ı çalıştırır."""
    print("--- Düğüm 5: E-posta Agent'ı Çalıştırılıyor... ---")
    status = run_email_agent() 
    return {"final_status": status}


workflow = StateGraph(WorkflowState)

workflow.add_node("news_agent", news_node)
workflow.add_node("risk_analyst", risk_analyst_node)
workflow.add_node("browser_agent", browser_node)
workflow.add_node("parser", parser_node)
workflow.add_node("save_to_db", save_to_db_node) 
workflow.add_node("email_agent", email_agent_node)


workflow.set_entry_point("news_agent")
workflow.add_edge("news_agent", "risk_analyst")
workflow.add_edge("risk_analyst", "browser_agent")
workflow.add_edge("browser_agent", "parser")
workflow.add_edge("parser", "save_to_db")
workflow.add_edge("save_to_db", "email_agent")
workflow.add_edge("email_agent", END)


app = workflow.compile()

if __name__ == "__main__":
    print("🚀 Agentic İş Akışı Başlatılıyor...")
    initial_state = {} 
    try:
        for event in app.stream(initial_state):
            node_name = list(event.keys())[0]
            print(f"✅ Düğüm Tamamlandı: {node_name}")
        print("\n🏁 Agentic İş Akışı Başarıyla Tamamlandı!")
    except Exception as e:
        print(f"\n❌ İŞ AKIŞI SIRASINDA BİR HATA OLUŞTU: {e}")
