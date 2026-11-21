import os
import requests

class SupabaseUploader:
    def __init__(self, supabase_url: str, supabase_key: str, bucket_name: str = "videos"):
        self.url = supabase_url.rstrip('/')
        self.key = supabase_key
        self.bucket = bucket_name

    def upload_local_video(self, file_path: str) -> str:
        """Envia um arquivo local ao Supabase e retorna sua URL pública."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        file_name = os.path.basename(file_path)
        upload_endpoint = f"{self.url}/storage/v1/object/{self.bucket}/{file_name}"

        headers = {
            "Authorization": f"Bearer {self.key}",
            "apikey": self.key,
            "x-upsert": "true"
        }

        with open(file_path, "rb") as f:
            response = requests.post(upload_endpoint, headers=headers, data=f)

        if response.status_code not in [200, 201]:
            raise Exception(f"Erro no upload para Supabase ({response.status_code}): {response.text}")

        # Retorna URL pública do arquivo
        return f"{self.url}/storage/v1/object/public/{self.bucket}/{file_name}"
