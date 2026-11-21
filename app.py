import streamlit as st
import os
import tempfile
from meta_api import MetaPublisher
from supabase_storage import SupabaseUploader
from csv_scheduler import CSVScheduler

st.set_page_config(page_title="Agendador de Reels Meta", page_icon="🚀")
st.title("🚀 Agendador de Reels Instagram & Facebook")

# Sidebar para credenciais
with st.sidebar:
    st.header("Configurações")
    ig_id = st.text_input("ID do Instagram", value=st.secrets.get("IG_ID", ""))
    token = st.text_input("Token Graph API", value=st.secrets.get("TOKEN", ""), type="password")
    supa_url = st.text_input("Supabase URL", value=st.secrets.get("SUPABASE_URL", ""))
    supa_key = st.text_input("Supabase Key", value=st.secrets.get("SUPABASE_KEY", ""), type="password")
    supa_bucket = st.text_input("Bucket Supabase", value="videos-reels")

uploaded_file = st.file_uploader("Envie seu arquivo CSV de agendamento", type=["csv"])

if st.button("▶️ Iniciar Agendamentos"):
    if not ig_id or not token or not uploaded_file:
        st.error("Preencha as credenciais e envie o arquivo CSV.")
    else:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_csv_path = tmp.name

        log_box = st.empty()
        def log_callback(msg):
            log_box.text(f"--> {msg}")

        try:
            publisher = MetaPublisher(ig_id, token)
            uploader = SupabaseUploader(supa_url, supa_key, bucket_name=supa_bucket) if supa_url and supa_key else None
            scheduler = CSVScheduler(tmp_csv_path, publisher, uploader)
            scheduler.processar_agendamentos(log_callback=log_callback)
            st.success("🎉 Todos os vídeos foram processados!")
        except Exception as e:
            st.error(f"Erro: {str(e)}")
        finally:
            if os.path.exists(tmp_csv_path):
                os.remove(tmp_csv_path)