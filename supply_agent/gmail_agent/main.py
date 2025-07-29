import os
import base64
import json
import pickle
from datetime import datetime
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import google.generativeai as genai
from pymongo import MongoClient

system_prompt = """
You are a professional supply chain assistant writing on behalf of Ford Otosan.
Your mission is to obtain price quotations for specific quantities from suppliers, using the conversation history.

YOUR RULES:
1.  Quote Collection: Your goal is to get a clear and specific price quote. Ask direct questions, for example, "What is your unit price for 10,000 units of steel plates?".
2.  Approval Prohibition: NEVER approve a quote, accept an offer, or make a purchase. Your task is solely to gather information. Approval processes will be handled by humans.
3.  Stop Condition: If the supplier's last email contains a clear price quote, add a special tag to the end of your generated response: [STOP_CONVERSATION]. For example, generate a response like, "Thank you for your quote. Our relevant department will review it. [STOP_CONVERSATION]".
4.  Language: Always use formal, professional, and polite language. Keep your answers concise and always end with 'Best regards, Ford Otosan Supply Chain Management'.
5.  Discount: If the message concerns pricing, proactively offer a discount for bulk purchase quantities, in a polite and professional manner.
"""

client = None
generative_model = None
SENDER_EMAIL = None

try:
    MONGO_URI = os.environ.get('MONGO_URI')
    DB_NAME = os.environ.get('DB_NAME')
    SENDER_EMAIL = os.environ.get('SENDER_EMAIL')
    api_key = os.environ.get('GOOGLE_API_KEY')

    if not all([MONGO_URI, DB_NAME, SENDER_EMAIL, api_key]):
        raise ValueError("Ortam değişkenlerinden biri eksik. MONGO_URI, DB_NAME, SENDER_EMAIL, GOOGLE_API_KEY kontrol edin.")

    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    conversations_collection = db.get_collection("conversations")
    genai.configure(api_key=api_key)
    generative_model = genai.GenerativeModel('gemini-1.5-flash-latest', system_instruction=system_prompt)
    print("Servisler başarıyla başlatıldı.")
except Exception as e:
    print(f"HATA: Genel başlatma sırasında bir sorun oluştu: {e}")


def get_gmail_service():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise Exception("Gmail token'ı geçersiz veya bulunamadı. Lütfen token.pickle dosyasını kodla birlikte deploy edin.")
    return build('gmail', 'v1', credentials=creds)

def get_email_body(payload):
    if "parts" in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body'].get('data')
                return base64.urlsafe_b64decode(data).decode('utf-8') if data else ""
            elif "parts" in part:
                body = get_email_body(part)
                return body if body else ""
    elif "body" in payload:
        data = payload['body'].get('data')
        return base64.urlsafe_b64decode(data).decode('utf-8') if data else ""
    return ""

def get_subject_from_headers(headers):
    for h in headers:
        if h['name'].lower() == 'subject':
            return h['value']
    return "No Subject"

def extract_sender(headers):
    for h in headers:
        if h['name'].lower() == 'from':
            return h['value']
    return ""

def send_reply(service, to, subject, body, thread_id):
    message = MIMEText(body, 'plain', 'utf-8')
    message['to'] = to
    message['from'] = SENDER_EMAIL
    message['subject'] = subject
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    return service.users().messages().send(userId='me', body={'raw': raw_message, 'threadId': thread_id}).execute()

# --- ANA CLOUD FUNCTION (PUB/SUB İÇİN) ---
def check_and_reply(event, context):
    if not client or not generative_model:
        print("HATA: Servisler başlatılamadığı için işlem durduruldu.")
        return

    print(f"Pub/Sub tarafından tetiklendi. Event ID: {context.event_id}")
    try:
        gmail_service = get_gmail_service()
        results = gmail_service.users().messages().list(userId='me', q="is:unread from:(-me)").execute()
        messages = results.get('messages', [])

        if not messages:
            print("Yeni yanıt bulunamadı.")
            return
        
        print(f"{len(messages)} okunmamış mesaj bulundu. İşleniyor...")
        for msg_summary in messages:
            msg_id = msg_summary['id']
            thread_id = msg_summary['threadId']
            conversation = conversations_collection.find_one({"threadId": thread_id})

            if not conversation:
                print(f"Thread {thread_id} veritabanında bulunamadı, atlanıyor.")
                continue
            
            full_message = gmail_service.users().messages().get(userId='me', id=msg_id).execute()
            user_reply_text = get_email_body(full_message['payload']).strip()

            if not user_reply_text:
                print(f"Mesaj {msg_id} için metin gövdesi bulunamadı, atlanıyor.")
                continue

            history_for_gemini = [
                {'role': 'model' if msg.get('role') == 'model' else 'user', 'parts': [msg.get('content', '')]}
                for msg in conversation.get('messages', []) if msg.get('content')
            ]

            chat_session = generative_model.start_chat(history=history_for_gemini)
            response = chat_session.send_message(user_reply_text)
            ai_reply_text = response.text


            subject = get_subject_from_headers(full_message['payload']['headers'])
            to_email = extract_sender(full_message['payload']['headers'])
            send_reply(
                service=gmail_service,
                to=to_email,
                subject="Re: " + subject,
                body=ai_reply_text,
                thread_id=thread_id
            )

            
            conversations_collection.update_one(
                {"threadId": thread_id},
                {"$push": {"messages": {"role": "model", "content": ai_reply_text}}}
            )

            
            gmail_service.users().messages().modify(userId='me', id=msg_id, body={'removeLabelIds': ['UNREAD']}).execute()

    except Exception as e:
        print(f"HATA: Ana işlem sırasında bir sorun oluştu: {e}")
            
    print("Kontrol tamamlandı.")
    return
