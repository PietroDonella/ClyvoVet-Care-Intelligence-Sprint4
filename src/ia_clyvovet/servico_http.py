"""API HTTP que a interface do plantão e a visão do tutor consomem."""

from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from . import ia_generativa
from .avaliacao import quadro_personalizacao, texto_relatorio
from .orquestrador import CareIntelligence
from .validacao import DadosInvalidos


class Aplicacao:
    def __init__(self, pasta_dados: Path, pasta_web: Path, clinica: dict | None = None):
        self.pasta_dados = Path(pasta_dados)
        self.pasta_web = Path(pasta_web)
        self._lock = threading.Lock()
        self.ia = CareIntelligence(self.pasta_dados, clinica=clinica)

    def saude(self) -> dict:
        with self._lock:
            return {
                "servico": "clyvovet-care-intelligence",
                "sprint": 4,
                "pets": len(self.ia.pets),
                "leituras": len(self.ia.leituras),
                "validacao": "ok",
            }

    def avaliacao(self) -> dict:
        with self._lock:
            return {
                "texto": texto_relatorio(self.ia),
                "leitura_27": quadro_personalizacao(27.0),
                "leitura_21": quadro_personalizacao(21.0),
            }

    def fila(self) -> list[dict]:
        with self._lock:
            return [item.to_dict() for item in self.ia.fila_prioridade()]

    def pet(self, id_pet: int) -> dict | None:
        with self._lock:
            if id_pet not in self.ia.pets_por_id:
                return None
            return self.ia.analisar_pet(id_pet).to_dict()

    def prompts(self, id_pet: int) -> dict | None:
        with self._lock:
            if id_pet not in self.ia.pets_por_id:
                return None
            insight = self.ia.analisar_pet(id_pet)
            return {
                "tutor": insight.prompt_tutor,
                "veterinario": insight.prompt_veterinario,
            }

    def listar_tutores(self) -> list[dict]:
        with self._lock:
            return [
                {"id_tutor": tutor["id_tutor"], "nome": tutor["nome"]}
                for tutor in sorted(self.ia.tutores.values(), key=lambda item: item["id_tutor"])
            ]

    def jornada_tutor(self, id_tutor: int) -> dict | None:
        with self._lock:
            tutor = self.ia.tutores.get(id_tutor)
            if tutor is None:
                return None
            pets = []
            for pet in self.ia.pets:
                if pet.id_tutor != id_tutor:
                    continue
                insight = self.ia.analisar_pet(pet.id_pet)
                escolhidas = ia_generativa.selecionar_para_tutor(insight.recomendacoes)
                pets.append(
                    {
                        "id_pet": pet.id_pet,
                        "nome": pet.nome,
                        "especie": pet.especie,
                        "idade": pet.idade,
                        "peso": pet.peso,
                        "nivel_risco": insight.nivel_risco,
                        "mensagem_tutor": insight.mensagem_tutor,
                        "recomendacoes": [
                            {
                                "servico": item.servico,
                                "motivo": ia_generativa.motivo_para_tutor(item),
                                "prioridade": item.prioridade,
                            }
                            for item in escolhidas
                        ],
                    }
                )
            return {
                "tutor": {
                    "id_tutor": tutor["id_tutor"],
                    "nome": tutor["nome"],
                    "telefone": tutor["telefone"],
                },
                "pets": pets,
            }

    def publicar_leitura(self, bruta: dict) -> tuple[int, dict]:
        with self._lock:
            try:
                self.ia.registrar_leitura(bruta)
            except DadosInvalidos as exc:
                return 400, {"erros": exc.erros}
            insight = self.ia.analisar_pet(bruta["pet_esperado_id"])
            return 201, insight.to_dict()

    def reiniciar(self) -> dict:
        with self._lock:
            self.ia.reiniciar()
            return {"ok": True, "leituras": len(self.ia.leituras)}


class _Tratador(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        if os.environ.get("CLYVO_HTTP_LOG") == "1":
            super().log_message(fmt, *args)

    def do_GET(self) -> None:
        caminho = urlparse(self.path).path
        aplicacao: Aplicacao = self.server.aplicacao  # type: ignore[attr-defined]
        if caminho == "/favicon.ico":
            self._vazio(204)
            return
        if caminho == "/api/saude":
            self._json(200, aplicacao.saude())
            return
        if caminho == "/api/fila":
            self._json(200, aplicacao.fila())
            return
        if caminho == "/api/avaliacao":
            self._json(200, aplicacao.avaliacao())
            return
        if caminho == "/api/tutores":
            self._json(200, aplicacao.listar_tutores())
            return
        if caminho.startswith("/api/tutores/"):
            id_tutor = _id(caminho.removeprefix("/api/tutores/"))
            if id_tutor is None:
                self._json(404, {"erro": "Tutor não encontrado."})
                return
            jornada = aplicacao.jornada_tutor(id_tutor)
            if jornada is None:
                self._json(404, {"erro": "Tutor não encontrado."})
                return
            self._json(200, jornada)
            return
        if caminho.startswith("/api/pets/") and caminho.endswith("/prompts"):
            id_pet = _id(caminho.removeprefix("/api/pets/").removesuffix("/prompts").strip("/"))
            if id_pet is None:
                self._json(404, {"erro": "Pet não encontrado."})
                return
            prompts = aplicacao.prompts(id_pet)
            if prompts is None:
                self._json(404, {"erro": "Pet não encontrado."})
                return
            self._json(200, prompts)
            return
        if caminho.startswith("/api/pets/"):
            id_pet = _id(caminho.removeprefix("/api/pets/"))
            if id_pet is None:
                self._json(404, {"erro": "Pet não encontrado."})
                return
            pet = aplicacao.pet(id_pet)
            if pet is None:
                self._json(404, {"erro": "Pet não encontrado."})
                return
            self._json(200, pet)
            return
        arquivo = {"/": "index.html", "/index.html": "index.html", "/app.js": "app.js", "/styles.css": "styles.css"}.get(caminho)
        if arquivo is None:
            self._json(404, {"erro": "Não encontrado."})
            return
        self._arquivo(arquivo)

    def do_POST(self) -> None:
        caminho = urlparse(self.path).path
        aplicacao: Aplicacao = self.server.aplicacao  # type: ignore[attr-defined]
        if caminho == "/api/reiniciar":
            self._json(200, aplicacao.reiniciar())
            return
        if caminho != "/api/leituras":
            self._json(404, {"erro": "Não encontrado."})
            return
        try:
            corpo = self._ler_json()
        except DadosInvalidos as exc:
            self._json(400, {"erros": exc.erros})
            return
        status, payload = aplicacao.publicar_leitura(corpo)
        self._json(status, payload)

    def _ler_json(self) -> dict:
        tamanho = int(self.headers.get("Content-Length") or "0")
        if tamanho <= 0 or tamanho > 100_000:
            raise DadosInvalidos(["Corpo da requisição vazio ou grande demais."])
        bruto = self.rfile.read(tamanho)
        try:
            corpo = json.loads(bruto.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise DadosInvalidos(["JSON inválido."]) from exc
        if not isinstance(corpo, dict):
            raise DadosInvalidos(["O corpo da leitura precisa ser um objeto JSON."])
        return corpo

    def _json(self, status: int, payload) -> None:
        corpo = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    def _vazio(self, status: int) -> None:
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _arquivo(self, nome: str) -> None:
        aplicacao: Aplicacao = self.server.aplicacao  # type: ignore[attr-defined]
        caminho = aplicacao.pasta_web / nome
        if not caminho.is_file():
            self._json(404, {"erro": "Arquivo da interface ausente."})
            return
        tipos = {
            "index.html": "text/html; charset=utf-8",
            "app.js": "text/javascript; charset=utf-8",
            "styles.css": "text/css; charset=utf-8",
        }
        corpo = caminho.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", tipos[nome])
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)


def _id(trecho: str) -> int | None:
    if not trecho.isdigit():
        return None
    return int(trecho)


def iniciar_servidor(aplicacao: Aplicacao, host: str = "127.0.0.1", porta: int = 8080) -> ThreadingHTTPServer:
    servidor = ThreadingHTTPServer((host, porta), _Tratador)
    servidor.aplicacao = aplicacao  # type: ignore[attr-defined]
    return servidor
