from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Pet:
    id_pet: int
    id_tutor: int
    nome: str
    especie: str
    cor: str
    idade: int
    peso: float
    rfid_uid: str
    status_internacao: str | None
    gaiola: str | None
    comportamento: str
    tutor_nome: str = ""
    tutor_telefone: str = ""


@dataclass
class LeituraIoT:
    timestamp: str
    origem: str
    topico: str
    gaiola: str
    temperatura: float
    umidade: float
    rfid_lido: str
    pet_esperado_id: int


@dataclass
class Alerta:
    codigo: str
    nivel: str
    titulo: str
    detalhe: str


@dataclass
class Recomendacao:
    servico: str
    motivo: str
    prioridade: int
    publico: str


@dataclass
class InsightPet:
    pet: Pet
    score_risco: int
    nivel_risco: str
    faixa_conforto: str
    internado: bool
    alertas: list[Alerta] = field(default_factory=list)
    recomendacoes: list[Recomendacao] = field(default_factory=list)
    mensagem_tutor: str = ""
    resumo_clinico: str = ""
    acao_priorizada: str = ""
    leitura: LeituraIoT | None = None
    prompt_tutor: str = ""
    prompt_veterinario: str = ""

    def to_dict(self) -> dict[str, Any]:
        pet = self.pet
        leitura = None
        if self.leitura is not None:
            leitura = {
                "timestamp": self.leitura.timestamp,
                "origem": self.leitura.origem,
                "topico": self.leitura.topico,
                "gaiola": self.leitura.gaiola,
                "temperatura": self.leitura.temperatura,
                "umidade": self.leitura.umidade,
                "rfid_lido": self.leitura.rfid_lido,
            }
        return {
            "id_pet": pet.id_pet,
            "nome": pet.nome,
            "especie": pet.especie,
            "cor": pet.cor,
            "idade": pet.idade,
            "peso": pet.peso,
            "rfid_uid": pet.rfid_uid,
            "id_tutor": pet.id_tutor,
            "tutor_nome": pet.tutor_nome,
            "tutor_telefone": pet.tutor_telefone,
            "status_internacao": pet.status_internacao,
            "gaiola": pet.gaiola,
            "comportamento": pet.comportamento,
            "faixa_conforto": self.faixa_conforto,
            "internado": self.internado,
            "score_risco": self.score_risco,
            "nivel_risco": self.nivel_risco,
            "acao_priorizada": self.acao_priorizada,
            "alertas": [a.__dict__ for a in self.alertas],
            "recomendacoes": [r.__dict__ for r in self.recomendacoes],
            "mensagem_tutor": self.mensagem_tutor,
            "resumo_clinico": self.resumo_clinico,
            "leitura": leitura,
        }
