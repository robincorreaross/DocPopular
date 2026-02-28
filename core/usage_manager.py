"""
usage_manager.py - Controla o consumo de auditorias IA diárias localmente.
"""

import json
import os
from datetime import date
from typing import Dict

class UsageManager:
    def __init__(self, storage_path: str = "usage.json"):
        # Se estiver no Windows e empacotado, pode ser necessário um caminho persistente
        self.storage_path = storage_path
        self.data = self._load()

    def _load(self) -> Dict:
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    return json.load(f)
            except:
                pass
        return {"date": str(date.today()), "count": 0}

    def _save(self) -> None:
        try:
            with open(self.storage_path, "w") as f:
                json.dump(self.data, f)
        except Exception as e:
            print(f"[DEBUG] Erro ao salvar uso: {e}")

    def get_count(self) -> int:
        """Retorna o número de auditorias feitas hoje."""
        today = str(date.today())
        if self.data.get("date") != today:
            self.data = {"date": today, "count": 0}
            self._save()
        return self.data.get("count", 0)

    def increment(self) -> None:
        """Incrementa o contador de hoje."""
        self.get_count() # Garante que a data está atualizada
        self.data["count"] += 1
        self._save()
