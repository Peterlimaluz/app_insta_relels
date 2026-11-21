import sys
import json
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QFileDialog, QTextEdit, QMessageBox)
from PySide6.QtCore import QThread, Signal

from meta_api import MetaPublisher
from supabase_storage import SupabaseUploader
from csv_scheduler import CSVScheduler

CONFIG_FILE = "config.json"


class WorkerThread(QThread):
    log_signal = Signal(str)
    finished_signal = Signal()

    def __init__(self, csv_path: str, config: dict, parent=None):
        super().__init__(parent)
        self.csv_path = csv_path
        self.config = config

    def run(self):
        try:
            publisher = MetaPublisher(self.config['ig_id'], self.config['token'])
            uploader = None
            if self.config.get('supabase_url') and self.config.get('supabase_key'):
                bucket = self.config.get('supabase_bucket', 'videos-reels')
                uploader = SupabaseUploader(self.config['supabase_url'], self.config['supabase_key'], bucket_name=bucket)

            scheduler = CSVScheduler(self.csv_path, publisher, uploader)
            scheduler.processar_agendamentos(log_callback=self.log_signal.emit)
            self.log_signal.emit("🎉 Todos os agendamentos foram concluídos com sucesso!")
        except Exception as e:
            self.log_signal.emit(f"❌ ERRO: {str(e)}")
        finally:
            self.finished_signal.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Agendador de Reels Meta & Supabase")
        self.resize(620, 580)
        self.worker_thread: WorkerThread | None = None  # Renomeado para evitar conflito com QObject.thread()

        main_layout = QVBoxLayout()

        # Inputs ID e Token
        self.ig_id_input = QLineEdit()
        self.ig_id_input.setPlaceholderText("ID da Conta do Instagram (ex: 1784146...)")
        
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Token de Acesso Meta Graph API")

        self.supa_url_input = QLineEdit()
        self.supa_url_input.setPlaceholderText("Supabase URL (ex: https://xyz.supabase.co)")

        self.supa_key_input = QLineEdit()
        self.supa_key_input.setPlaceholderText("Supabase Key")

        self.supa_bucket_input = QLineEdit()
        self.supa_bucket_input.setPlaceholderText("Nome do Bucket (Padrão: videos-reels)")

        main_layout.addWidget(QLabel("<b>Configurações Meta API:</b>"))
        main_layout.addWidget(self.ig_id_input)
        main_layout.addWidget(self.token_input)
        main_layout.addWidget(QLabel("<b>Configurações Supabase (Upload de Vídeos Locais):</b>"))
        main_layout.addWidget(self.supa_url_input)
        main_layout.addWidget(self.supa_key_input)
        main_layout.addWidget(self.supa_bucket_input)

        # Seleção de CSV
        csv_layout = QHBoxLayout()
        self.csv_path_input = QLineEdit()
        self.csv_path_input.setPlaceholderText("Selecione o arquivo CSV de agendamento...")
        btn_csv = QPushButton("Selecionar CSV")
        btn_csv.clicked.connect(self.browse_csv)
        csv_layout.addWidget(self.csv_path_input)
        csv_layout.addWidget(btn_csv)
        main_layout.addLayout(csv_layout)

        # Botões Salvar Config e Iniciar
        btn_save = QPushButton("💾 Salvar Credenciais")
        btn_save.clicked.connect(self.save_config)
        
        self.btn_run = QPushButton("▶️ Iniciar Agendamentos")
        self.btn_run.clicked.connect(self.start_processing)

        main_layout.addWidget(btn_save)
        main_layout.addWidget(self.btn_run)

        # Área de Logs
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        main_layout.addWidget(self.log_area)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.load_config()

    def browse_csv(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Selecionar CSV", "", "CSV Files (*.csv)")
        if file_name:
            self.csv_path_input.setText(file_name)

    def save_config(self):
        config = {
            "ig_id": self.ig_id_input.text().strip(),
            "token": self.token_input.text().strip(),
            "supabase_url": self.supa_url_input.text().strip(),
            "supabase_key": self.supa_key_input.text().strip(),
            "supabase_bucket": self.supa_bucket_input.text().strip() or "videos-reels"
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
        QMessageBox.information(self, "Sucesso", "Credenciais salvas com sucesso!")

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                self.ig_id_input.setText(config.get("ig_id", ""))
                self.token_input.setText(config.get("token", ""))
                self.supa_url_input.setText(config.get("supabase_url", ""))
                self.supa_key_input.setText(config.get("supabase_key", ""))
                self.supa_bucket_input.setText(config.get("supabase_bucket", "videos-reels"))

    def start_processing(self):
        csv_path_str: str = self.csv_path_input.text().strip()
        if not csv_path_str or not os.path.exists(csv_path_str):
            QMessageBox.warning(self, "Aviso", "Por favor, selecione um arquivo CSV válido.")
            return

        if not self.ig_id_input.text().strip() or not self.token_input.text().strip():
            QMessageBox.warning(self, "Aviso", "Preencha o ID da conta e Token do Instagram antes de iniciar.")
            return

        self.btn_run.setEnabled(False)
        self.log_area.append("Iniciando rotina de processamento...")

        config_data: dict = {
            "ig_id": self.ig_id_input.text().strip(),
            "token": self.token_input.text().strip(),
            "supabase_url": self.supa_url_input.text().strip(),
            "supabase_key": self.supa_key_input.text().strip(),
            "supabase_bucket": self.supa_bucket_input.text().strip() or "videos-reels"
        }

        # Instanciação da Thread renomeada para worker_thread
        self.worker_thread = WorkerThread(csv_path_str, config_data, parent=self)
        self.worker_thread.log_signal.connect(self.log_area.append)  # type: ignore
        self.worker_thread.finished_signal.connect(lambda: self.btn_run.setEnabled(True))  # type: ignore
        self.worker_thread.start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())