import pandas as pd
import datetime
import time
import os

class CSVScheduler:
    def __init__(self, csv_file_path: str, meta_publisher, supabase_uploader=None):
        self.csv_path = csv_file_path
        self.publisher = meta_publisher
        self.uploader = supabase_uploader

    def processar_agendamentos(self, log_callback=print):
        # Lê o CSV ignorando espaços após vírgulas
        try:
            df = pd.read_csv(self.csv_path, skipinitialspace=True)
        except Exception:
            df = pd.read_csv(self.csv_path, skipinitialspace=True, engine='python')
        
        # Garante a existência da coluna 'status' e força o tipo para objeto/texto
        if 'status' not in df.columns:
            df['status'] = ''
        
        df['status'] = df['status'].fillna('').astype(object)

        # Utiliza enumerate com start=1 para evitar o erro de tipagem no Hashable do pandas
        for line_num, (idx, row) in enumerate(df.iterrows(), start=1):
            # Pula itens já concluídos
            if str(row.get('status', '')).strip().upper() in ['CONCLUIDO', 'CONCLUÍDO']:
                continue

            video_input = str(row['video_path']).strip()
            titulo = str(row.get('titulo', '')).strip()
            descricao = str(row.get('descricao', '')).strip()
            link_compra = str(row.get('link_compra', '')).strip()
            
            caption = f"{titulo}\n\n{descricao}\n\n🛒 Compre aqui: {link_compra}"
            agendamento_str = str(row.get('agendamento_data_hora', '')).strip()

            # Trata formato da data e hora
            try:
                data_agendada = datetime.datetime.strptime(agendamento_str, "%Y-%m-%d %H:%M")
            except ValueError:
                try:
                    data_agendada = datetime.datetime.strptime(agendamento_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    log_callback(f"[AVISO] Data inválida na linha {line_num} ('{agendamento_str}'). Publicando imediatamente...")
                    data_agendada = datetime.datetime.now()

            agora = datetime.datetime.now()

            if agora < data_agendada:
                espera = (data_agendada - agora).total_seconds()
                log_callback(f"[AGUARDANDO] {int(espera)}s para publicar item {line_num}...")
                time.sleep(espera)

            # Upload de vídeo local ou URL pública
            if video_input.startswith("http://") or video_input.startswith("https://"):
                video_url = video_input
            else:
                log_callback(f"[UPLOAD] Upload do vídeo local para o Supabase: {video_input}")
                if not self.uploader:
                    raise ValueError("SupabaseUploader não configurado para vídeos locais.")
                video_url = self.uploader.upload_local_video(video_input)

            # Publicação na Graph API da Meta
            log_callback(f"[PUBLICANDO] Publicando vídeo {line_num} no Instagram/Facebook...")
            res = self.publisher.publicar_reels(video_url, caption)
            
            log_callback(f"[SUCESSO] Post ID: {res.get('id')}")
            
            # Grava a confirmação no CSV
            df.at[idx, 'status'] = 'CONCLUIDO'
            df.to_csv(self.csv_path, index=False)