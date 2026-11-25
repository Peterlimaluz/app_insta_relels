import os
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from typing import Optional

# Escopos para Upload e Gestão de Comentários
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl"
]

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

        # Se os escopos mudaram ou o token expirou, revalida
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

    def adicionar_comentario(self, video_id: str, texto_comentario: str, logger=print) -> bool:
        """Posta um comentário público no vídeo recém-publicado."""
        try:
            logger(f"  [YouTube] 💬 Publicando comentário com link no vídeo {video_id}...")
            body = {
                'snippet': {
                    'videoId': video_id,
                    'topLevelComment': {
                        'snippet': {
                            'textOriginal': texto_comentario
                        }
                    }
                }
            }
            self.youtube.commentThreads().insert(
                part="snippet",
                body=body
            ).execute()
            logger("  [YouTube] ✅ Comentário com link publicado com sucesso!")
            return True
        except Exception as e:
            logger(f"  [YouTube] ⚠️ Falha ao publicar comentário: {str(e)}")
            return False

    def postar_shorts(
        self, 
        caminho_video_local: str, 
        titulo: str, 
        descricao: str, 
        link_compra: Optional[str] = None, 
        tags: Optional[list] = None, 
        logger=print
    ) -> bool:
        try:
            logger("  [YouTube] Preparando metadados do Shorts...")
            
            titulo_final = f"{titulo[:90]} #Shorts"
            
            aviso_afiliado = (
                "\n\nAviso: Os links indicados são de afiliados. Ao comprar por eles, podemos receber uma comissão.\n\n#Shorts #Ofertas"
            )
            
            descricao_final = f"{descricao}{aviso_afiliado}"

            body = {
                'snippet': {
                    'title': titulo_final,
                    'description': descricao_final,
                    'tags': tags or ['Shorts', 'Achadinhos', 'Ofertas', 'Review'],
                    'categoryId': '22'  # People & Blogs
                },
                'status': {
                    'privacyStatus': 'public',
                    'selfDeclaredMadeForKids': False
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

            # Posta automaticamente o comentário com o link logo após o upload
            if link_compra and link_compra.strip():
                comentario = (
                    f"🛒 Compre aqui: {link_compra.strip()}\n\n"
                    f"⚡ Oferta por tempo limitado! Aproveite antes que acabe o estoque."
                )
                self.adicionar_comentario(video_id, comentario, logger=logger)

            return True

        except Exception as e:
            logger(f"  [YouTube] ❌ Erro ao enviar Shorts: {str(e)}")
            return False