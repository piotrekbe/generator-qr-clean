import streamlit as st
import pandas as pd
import segno
from fpdf import FPDF
import io
import zipfile
import os

# --- KONFIGURACJA PRO ---
st.set_page_config(page_title="QR Generator ONLY", page_icon="🔳", layout="centered")

def generate_pdf(qr_code_data):
    # Tworzymy PDF 100x100mm
    pdf = FPDF(unit="mm", format=(100, 100))
    pdf.set_auto_page_break(False, margin=0)
    pdf.add_page()
    
    # Generowanie kodu QR
    qr = segno.make_qr(str(qr_code_data))
    img_buffer = io.BytesIO()
    # Skala 15 sprawi, że kod będzie duży i wyraźny na środku strony
    qr.save(img_buffer, kind='png', scale=15, border=2)
    img_buffer.seek(0)
    
    # Wyśrodkowanie kodu na stronie 100x100
    # Zakładając szerokość ok 70mm, x=15 ( (100-70)/2 )
    pdf.image(img_buffer, x=15, y=15, w=70)
    
    return pdf.output()

# --- LOGIKA APLIKACJI ---

st.title("🔳 Generator SAMYCH Kodów QR")
st.info("Aplikacja generuje pliki PDF zawierające wyłącznie kod QR (bez tekstów i kwot).")
st.markdown("---")

uploaded_file = st.file_uploader("Wgraj plik CSV", type="csv")

if uploaded_file:
    @st.cache_data
    def process_csv(file_bytes):
        content = file_bytes.decode("utf-8").splitlines()
        if not content: return "Paczka", []
        
        # Pierwszy wiersz to nazwa paczki (np. Gala26_Kawa)
        package_name = content[0].strip().replace(" ", "_")
        # Kody zaczynają się od drugiego wiersza
        k_raw = content[1:]
        
        return package_name, [k.strip() for k in k_raw if k.strip()]

    package_name, all_kody = process_csv(uploaded_file.getvalue())
    total = len(all_kody)
    
    st.success(f"Wczytano {total} kodów. Nazwa projektu: **{package_name}**")

    batch_size = 2000
    num_batches = (total + batch_size - 1) // batch_size

    selected_batch = st.selectbox(
        "Wybierz partię do procesowania:", 
        range(num_batches), 
        format_func=lambda x: f"Partia {x+1}: rekordy {x*batch_size + 1} - {min((x+1)*batch_size, total)}"
    )

    s_idx = selected_batch * batch_size
    e_idx = min((selected_batch + 1) * batch_size, total)
    current_batch = all_kody[s_idx:e_idx]

    c1, c2 = st.columns(2)
    c1.metric("Pierwszy kod w partii", current_batch[0])
    c2.metric("Ostatni kod w partii", current_batch[-1])

    if st.button(f"🔥 Generuj Partię {selected_batch + 1}", use_container_width=True):
        zip_buffer = io.BytesIO()
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for i, kod in enumerate(current_batch):
                # Numeracja: Numer wiersza w CSV (kody zaczynają się od wiersza 2)
                row_number = s_idx + i + 2
                
                pdf_data = generate_pdf(kod)
                filename = f"{row_number}_{kod}.pdf"
                zf.writestr(filename, pdf_data)
                
                if i % 20 == 0 or (i + 1) == len(current_batch):
                    p = (i + 1) / len(current_batch)
                    progress_bar.progress(p)
                    status_text.text(f"Postęp: {int(p*100)}%")
        
        st.session_state['ready_zip_only'] = zip_buffer.getvalue()
        st.session_state['current_batch_only'] = selected_batch + 1

    if 'ready_zip_only' in st.session_state and st.session_state.get('current_batch_only') == selected_batch + 1:
        st.divider()
        st.download_button(
            label=f"✅ POBIERZ PACZKĘ: {package_name}_partia_{st.session_state['current_batch_only']}",
            data=st.session_state['ready_zip_only'],
            file_name=f"{package_name}_partia_{st.session_state['current_batch_only']}.zip",
            mime="application/zip",
            use_container_width=True
        )
