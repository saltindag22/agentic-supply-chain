import streamlit as st
import subprocess
import sys
import json
import re
import time
import os

def add_bg_from_url_and_style():
    """
    İnternet'teki bir resim URL'si ile arka plan ekler ve okunabilirliği artırmak
    için ana içerik alanına yarı saydam bir katman uygular.
    """
    image_url = "https://www.fordotosan.com.tr/documents/Ford-Otosan-Basin-Bulteni-Fotograflari/yenikoy_fabrika_gokyuzu.jpg"
    
    st.markdown(
         f"""
         <style>
         /* Ana uygulama konteynerine arka plan resmini ekle */
         .stApp {{
             background-image: url("{image_url}");
             background-attachment: fixed;
             background-size: cover;
         }}

         /* Okunabilirliği artırmak için ana içerik alanına yarı saydam bir katman ekle */
         [data-testid="main-container"] > div {{
             background-color: rgba(240, 242, 246, 0.9); /* %90 opaklıkta açık gri */
             padding: 2rem;
             border-radius: 10px;
         }}
         </style>
         """,
         unsafe_allow_html=True
     )


st.set_page_config(
    page_title="Ford Otosan | Agentic Supply Chain",
    page_icon="🤖",
    layout="wide"
)

add_bg_from_url_and_style()

st.title("🤖 Agentic Tedarik Zinciri Risk Yönetimi")
st.caption("Bu uygulama, güncel haberleri analiz ederek potansiyel tedarik zinciri risklerini belirler, alternatif tedarikçiler bulur ve onlarla ilk teması kurar.")


def clean_ansi_escape_codes(text):
    """Removes ANSI escape codes from a string."""
    ansi_escape = re.compile(r'\x1b\[[0-9;]*[mK]')
    return ansi_escape.sub('', text)


if st.button('İş Akışını Başlat', type="primary", use_container_width=True):
    
    
    results_container = st.container(border=True)
    
    
    with results_container:
        st.info("İş akışı başlatıldı... Lütfen bekleyin. Bu işlem birkaç dakika sürebilir.")
        st.subheader("Akış Adımları ve Çıktıları")
        
        log_expander = st.expander("Tüm Akış Günlüğünü (Raw Log) Görüntüle")
        log_placeholder = log_expander.empty()
        
        step1_placeholder = st.empty()
        step2_placeholder = st.empty()
        step3_placeholder = st.empty()
        step4_placeholder = st.empty()
        step5_placeholder = st.empty()
        step6_placeholder = st.empty()
        final_status_placeholder = st.empty()
        gif_placeholder = st.empty() 

    full_log = ""

    try:
        process = subprocess.Popen(
            [sys.executable, "main_orchestrator.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, 
            text=True,
            encoding='utf-8',
            bufsize=1 
        )

        raw_browser_output = ""
        capturing_browser_output = False
        
        
        for line in iter(process.stdout.readline, ''):
            clean_line = clean_ansi_escape_codes(line.strip())
            full_log += clean_line + "\n"
            log_placeholder.code(full_log, language="log")

            
            if "Düğüm 1: Haberler Çekiliyor" in clean_line:
                step1_placeholder.status("Adım 1: Haberler Taranıyor...", state="running")
            
            
            if "Düğüm 2: Risk Analizi Yapılıyor" in clean_line:
                step1_placeholder.status("Adım 1: Haberler Taranıyor...", state="complete")
                step2_placeholder.status("Adım 2: Risk Analizi Yapılıyor ve Arama Sorgusu Üretiliyor...", state="running")

            if "Yeni arama sorgusu:" in clean_line:
                search_prompt = clean_line.split("Yeni arama sorgusu:", 1)[1].strip()
                with step2_placeholder.container():
                    st.write("**Adım 2: Risk Analizi**")
                    st.success("Risk analizi tamamlandı. Web araştırması için aşağıdaki sorgu üretildi:")
                    st.code(search_prompt, language='text')

            
            if "Düğüm 3: Web'de Araştırma Yapılıyor" in clean_line:
                step3_placeholder.status("Adım 3: Alternatif Tedarikçiler İçin Web'de Araştırma Yapılıyor...", state="running")
                capturing_browser_output = True
            
            if "Düğüm 4: Araştırma Sonuçları Ayıklanıyor" in clean_line:
                capturing_browser_output = False
                with step3_placeholder.container():
                     st.write("**Adım 3: Web Araştırması**")
                     st.success("Web araştırması tamamlandı.")
                     with st.expander("Browser Agent'ın Ham Çıktısını Görüntüle"):
                         st.text(raw_browser_output)

            if capturing_browser_output and "Düğüm 3:" not in clean_line:
                 raw_browser_output += line

            
            if "Düğüm 4: Araştırma Sonuçları Ayıklanıyor" in clean_line:
                 step4_placeholder.status("Adım 4: Tedarikçi Bilgileri Ayıklanıyor ve Temizleniyor...", state="running")

            if "Ayıklanan Tedarikçiler" in clean_line:
                try:
                    json_str = clean_line.split("JSON):", 1)[1].strip()
                    suppliers_data = json.loads(json_str)
                    with step4_placeholder.container():
                        st.write("**Adım 4: Tedarikçi Bilgilerinin Ayıklanması**")
                        if suppliers_data:
                            st.success(f"{len(suppliers_data)} adet geçerli tedarikçi bilgisi (isim ve email) başarıyla ayıklandı.")
                            st.json(suppliers_data)
                        else:
                            st.warning("Araştırma sonucunda geçerli bir tedarikçi bilgisi bulunamadı.")
                except (json.JSONDecodeError, IndexError) as e:
                    with step4_placeholder.container():
                        st.write("**Adım 4: Tedarikçi Bilgilerinin Ayıklanması**")
                        st.error(f"Tedarikçi verisi ayıklanırken bir hata oluştu: {e}")
                        st.text(clean_line)
            
            
            if "Veritabanına Kaydediliyor" in clean_line:
                step5_placeholder.status("Adım 5: Tedarikçi Listesi Veritabanına Kaydediliyor...", state="running")
            
            if "yeni tedarikçi veritabanına eklendi" in clean_line:
                with step5_placeholder.container():
                    st.write("**Adım 5: Veritabanına Kayıt**")
                    st.success(clean_line)

           
            if "Düğüm 5: E-posta Agent'ı" in clean_line:
                step6_placeholder.status("Adım 6: Bulunan Tedarikçilere İlk Temas E-postaları Gönderiliyor...", state="running")

            if "E-postalar gönderildi ve durumlar güncellendi" in clean_line:
                with step6_placeholder.container():
                    st.write("**Adım 6: E-posta Gönderimi**")
                    st.success("Tedarikçilerle ilk temas başarıyla kuruldu.")

            
            if "İş Akışı Başarıyla Tamamlandı" in clean_line:
                final_status_placeholder.success("🏁 Agentic İş Akışı Başarıyla Tamamlandı!")
                st.balloons()
                
        process.wait() 
        
        
        gif_path = "agent_history.gif"
        if os.path.exists(gif_path):
            time.sleep(1)
            with gif_placeholder.container():
                st.subheader("🤖 Agent Akışının Görsel Özeti")
                st.image(gif_path)
        
        if process.returncode != 0:
            final_status_placeholder.error(f"İş akışı bir hata ile sonlandı. Lütfen logları kontrol edin.")
            st.code(full_log, language="log")

    except Exception as e:
        st.error(f"Frontend uygulamasında bir hata oluştu: {e}")
