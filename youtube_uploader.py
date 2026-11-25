import os
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from typing import Optional

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

class YouTubeShortsPublisher:
    def __init__(self, secrets_file="client_secrets.json", token_file="youtube_token.pickle"):
        self.secrets_file = secrets_file
        self.token_file = token_file
        self.youtube = self._autenticar()

    def _autenticar(self):
        creds = None
        if os.path.exists(self.token_file):
            with open(self.token_file, "rb") as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.secrets_file):
                    raise FileNotFoundError(f"Arquivo {self.secrets_file} não encontrado na raiz.")
                flow = InstalledAppFlow.from_client_secrets_file(self.secrets_file, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self.token_file, "wb") as token:
                pickle.dump(creds, token)

        return build("youtube", "v3", credentials=creds)

    def postar_shorts(self, caminho_video_local: str, titulo: str, descricao: str, tags: Optional[list] = None, logger=print) -> bool:
        try:
            logger("  [YouTube] Preparando metadados do Shorts...")
            
            # Garantir a tag #Shorts para classificação imediata
            titulo_final = f"{titulo[:90]} #Shorts"
            descricao_final = f"{descricao}\n\n#Shorts"
            tags_finais = tags or ["Shorts", "Ofertas", "Amazon"]

            body = {
                "snippet": {
                    "title": titulo_final,
                    "description": descricao_final,
                    "tags": tags_finais,
                    "categoryId": "22" # Pessoas e blogs
                },
                "status": {
                    "privacyStatus": "public",
                    "selfDeclaredMadeForKids": False
                }
            }

            media = MediaFileUpload(caminho_video_local, mimetype="video/mp4", resumable=True)
            request = self.youtube.videos().insert(part="snippet,status", body=body, media_body=media)

            logger("  [YouTube] Iniciando upload do arquivo local...")
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progresso = int(status.progress() * 100)
                    logger(f"  [YouTube] Progresso: {progresso}%")

            video_id = response.get("id")
            logger(f"  [YouTube] ✅ Shorts publicado com sucesso: https://youtube.com/shorts/{video_id}")
            return True

        except Exception as e:
            logger(f"  [YouTube] ❌ Erro ao enviar Shorts: {str(e)}")
            return False