import os
import sys
import datetime
import pandas as pd
from meta_api import MetaPublisher
from supabase_storage import SupabaseUploader
from youtube_uploader import YouTubeShortsPublisher

CSV_FILE = os.getenv("CSV_FILE_PATH", "agendamento.csv")
BRASILIA_TZ = datetime.timezone(datetime.timedelta(hours=-3))

def run():
    ig_id = os.getenv("IG_ID")
    # Lê META_TOKEN ou TOKEN para evitar divergência com o GitHub Secrets
    token = os.getenv("META_TOKEN") or os.getenv("TOKEN")
    fb_page_id = os.getenv("FB_PAGE_ID")
    supa_url = os.getenv("SUPABASE_URL")
    supa_key = os.getenv("SUPABASE_KEY")
    supa_bucket = os.getenv("SUPABASE_BUCKET", "videos-reels")

    # Diagnóstico explícito para o log de QA
    if not ig_id:
        print("❌ Erro: Variável de ambiente IG_ID não foi encontrada.")
    if not token:
        print("❌ Erro: Variável de ambiente META_TOKEN/TOKEN não foi encontrada.")

    if not ig_id or not token:
        sys.exit(1)

    if not os.path.exists(CSV_FILE):
        print(f"⚠️ Arquivo CSV '{CSV_FILE}' não encontrado. Encerrando.")
        return

    # Lê o CSV de forma segura
    try:
        df = pd.read_csv(CSV_FILE, skipinitialspace=True)
    except Exception:
        df = pd.read_csv(CSV_FILE, skipinitialspace=True, engine='python')

    if 'status' not in df.columns:
        df['status'] = ''

    df['status'] = df['status'].astype(str).fillna('')

    publisher = MetaPublisher(ig_id, token, facebook_page_id=fb_page_id)
    uploader = None
    yt_publisher = YouTubeShortsPublisher()
    if supa_url and supa_key:
        uploader = SupabaseUploader(supa_url, supa_key, bucket_name=supa_bucket)

    agora = datetime.datetime.now(BRASILIA_TZ)
    houve_postagem = False

    print(f"🔍 Verificando agendamentos em {CSV_FILE} (Horário atual do servidor: {agora.strftime('%Y-%m-%d %H:%M:%S')})...")

    for line_num, (idx, row) in enumerate(df.iterrows(), start=1):
        status = str(row.get('status', '')).strip().upper()
        if status in ['CONCLUIDO', 'CONCLUÍDO']:
            continue

        agendamento_str = str(row.get('agendamento_data_hora', '')).strip()
        try:
            data_agendada = datetime.datetime.strptime(
                agendamento_str, "%Y-%m-%d %H:%M"
            ).replace(tzinfo=BRASILIA_TZ)
        except ValueError:
            try:
                data_agendada = datetime.datetime.strptime(
                    agendamento_str, "%Y-%m-%d %H:%M:%S"
                ).replace(tzinfo=BRASILIA_TZ)
            except ValueError:
                print(f"⚠️ Data inválida na linha {line_num} ('{agendamento_str}'). Ignorando.")
                continue

        # Verifica se o horário agendado já chegou ou passou
        if agora >= data_agendada:
            video_input = str(row['video_path']).strip()
            titulo = str(row.get('titulo', '')).strip()
            descricao = str(row.get('descricao', '')).strip()
            link_compra = str(row.get('link_compra', '')).strip()
            caption = f"{titulo}\n\n{descricao}\n\n🛒 Compre aqui: {link_compra}"

            print(f"🚀 Horário atingido para o item da linha {line_num} (Agendado: {agendamento_str}). Publicando...")

            try:
                # 1. Tratamento para o Instagram / Meta (Requer URL pública)
                if video_input.startswith("http://") or video_input.startswith("https://"):
                    video_url = video_input
                    caminho_local_yt = None
                else:
                    if not uploader:
                        raise ValueError("SupabaseUploader não configurado para vídeos locais.")
                    print(f"📤 Upload do vídeo local para o Supabase: {video_input}")
                    video_url = uploader.upload_local_video(video_input)
                    caminho_local_yt = video_input

                # 2. Publicação na Meta (Instagram e Facebook Page)
                res = publisher.publicar_reels(video_url, caption)
                print(f"✅ Sucesso na Meta! Post ID: {res.get('id')}")

                # 3. Publicação no YouTube Shorts
                if caminho_local_yt and os.path.exists(caminho_local_yt):
                    print(f"🎬 Enviando para o YouTube Shorts: {caminho_local_yt}")
                    sucesso_yt = yt_publisher.postar_shorts(
                        caminho_video_local=caminho_local_yt,
                        titulo=titulo if titulo else "Oferta Imperdível",
                        descricao=caption,
                        logger=print
                    )
                    if sucesso_yt:
                        print("✅ Sucesso no YouTube Shorts!")
                    else:
                        print("⚠️ Falha ao publicar no YouTube Shorts.")
                else:
                    print("⚠️ Vídeo local não encontrado para envio direto ao YouTube Shorts.")

                df.at[idx, 'status'] = 'CONCLUIDO'
                houve_postagem = True
            except Exception as e:
                print(f"❌ Erro ao publicar item {line_num}: {e}")
        else:
            diferenca_min = int((data_agendada - agora).total_seconds() / 60)
            print(f"⏳ Item {line_num} agendado para {agendamento_str} (faltam {diferenca_min} min). Pulando.")

    if houve_postagem:
        df.to_csv(CSV_FILE, index=False)
        print(f"💾 {CSV_FILE} atualizado com os novos status no repositório.")
    else:
        print("ℹ️ Nenhuma postagem pendente para o horário atual.")

if __name__ == "__main__":
    run()