from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import pickle

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'
]

def main():
    """
    Kullanıcıdan Gmail API için yetki alır ve token.pickle dosyasını oluşturur.
    Bu script'i sadece bir kez çalıştırmanız yeterlidir.
    """
    creds = None
    if os.path.exists('token.pickle'):
        print("Mevcut token.pickle dosyası bulundu. İşlem atlanıyor.")
        return

    print("Gmail API için yetkilendirme süreci başlatılıyor...")
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)

    with open('token.pickle', 'wb') as token:
        pickle.dump(creds, token)
    
    print("\nYetkilendirme başarılı! 'token.pickle' dosyası oluşturuldu.")
    print("Bu dosyayı ve credentials.json dosyasını güvende tutun.")

if __name__ == '__main__':
    main()