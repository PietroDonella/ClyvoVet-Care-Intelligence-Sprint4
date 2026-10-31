from __future__ import annotations

import json
from pathlib import Path

from . import ia_generativa, motor_regras, recomendador
from .modelos import InsightPet, LeituraIoT, Pet
from .validacao import DadosInvalidos, validar_base, validar_leitura


class CareIntelligence:
    """Junta regras, recomendação e texto para um pet ou para a fila do plantão."""

    def __init__(self, pasta_dados: Path, clinica: dict | None = None):
        self.pasta_dados = Path(pasta_dados)
        self._clinica_injetada = clinica
        self.tutores: dict[int, dict] = {}
        self.pets: list[Pet] = []
        self.pets_por_id: dict[int, Pet] = {}
        self.pets_por_rfid: dict[str, Pet] = {}
        self.prontuarios: list[dict] = []
        self.consultas: list[dict] = []
        self.vacinas: list[dict] = []
        self.medicamentos: list[dict] = []
        self.leituras: list[LeituraIoT] = []
        self.reiniciar()

    def reiniciar(self) -> None:
        if self._clinica_injetada is None:
            clinica = json.loads(
                (self.pasta_dados / "base_clinica.json").read_text(encoding="utf-8")
            )
        else:
            clinica = self._clinica_injetada
        iot = json.loads((self.pasta_dados / "leituras_iot.json").read_text(encoding="utf-8"))
        erros = validar_base(clinica, iot["leituras"])
        if erros:
            raise DadosInvalidos(erros)

        self.tutores = {t["id_tutor"]: t for t in clinica["tutores"]}
        self.pets = [self._montar_pet(p) for p in clinica["pets"]]
        self.pets_por_id = {p.id_pet: p for p in self.pets}
        self.pets_por_rfid = {p.rfid_uid.upper(): p for p in self.pets}
        self.prontuarios = clinica["prontuarios"]
        self.consultas = clinica["consultas"]
        self.vacinas = clinica["vacinas"]
        self.medicamentos = clinica["medicamentos"]
        self.leituras = [LeituraIoT(**item) for item in iot["leituras"]]

    def registrar_leitura(self, bruta: dict) -> None:
        erros = validar_leitura(bruta, set(self.pets_por_id))
        if erros:
            raise DadosInvalidos(erros)
        self.leituras.append(
            LeituraIoT(
                timestamp=bruta["timestamp"],
                origem=bruta["origem"],
                topico=bruta["topico"],
                gaiola=bruta["gaiola"],
                temperatura=float(bruta["temperatura"]),
                umidade=float(bruta["umidade"]),
                rfid_lido=str(bruta["rfid_lido"]),
                pet_esperado_id=bruta["pet_esperado_id"],
            )
        )

    def leitura_atual(self, id_pet: int) -> LeituraIoT | None:
        escolhida = None
        for leitura in self.leituras:
            if leitura.pet_esperado_id != id_pet:
                continue
            if escolhida is None or leitura.timestamp >= escolhida.timestamp:
                escolhida = leitura
        return escolhida

    def _montar_pet(self, bruto: dict) -> Pet:
        tutor = self.tutores[bruto["id_tutor"]]
        return Pet(
            id_pet=bruto["id_pet"],
            id_tutor=bruto["id_tutor"],
            nome=bruto["nome"],
            especie=bruto["especie"],
            cor=bruto["cor"],
            idade=bruto["idade"],
            peso=bruto["peso"],
            rfid_uid=bruto["rfid_uid"],
            status_internacao=bruto["status_internacao"],
            gaiola=bruto["gaiola"],
            comportamento=bruto["comportamento"],
            tutor_nome=tutor["nome"],
            tutor_telefone=tutor["telefone"],
        )

    def analisar_pet(self, id_pet: int) -> InsightPet:
        pet = self.pets_por_id[id_pet]
        leitura = self.leitura_atual(pet.id_pet)
        alertas = []
        score = 0
        internado = pet.status_internacao == "Internado"

        if leitura is not None:
            score_iot, alertas_iot = motor_regras.avaliar_ambiente(pet, leitura)
            score += score_iot
            alertas.extend(alertas_iot)
            alertas.extend(
                motor_regras.avaliar_identificacao(pet, self.pets_por_rfid, leitura)
            )

        tem_critico = any(a.nivel == "critico" for a in alertas)
        if tem_critico:
            score = max(score, 90)

        nivel = motor_regras.nivel_de_score(score, tem_critico)
        _, _, _, _, faixa = motor_regras.faixa_conforto(pet)
        clima_fora_faixa = any(a.codigo in {"IOT_TERMICO", "IOT_UMIDADE"} for a in alertas)
        identidade_divergente = any(
            a.codigo in {"RFID_TROCA_PACIENTE", "RFID_DESCONHECIDO"} for a in alertas
        )
        recs = recomendador.recomendar(
            pet=pet,
            vacinas=self.vacinas,
            prontuarios=self.prontuarios,
            consultas=self.consultas,
            medicamentos=self.medicamentos,
            internado=internado,
            nivel_risco=nivel,
            clima_fora_faixa=clima_fora_faixa,
            identidade_divergente=identidade_divergente,
        )

        if tem_critico:
            acao = "Conferir identidade RFID e interromper procedimento até validar o paciente."
        elif nivel == "alto":
            acao = "Priorizar este animal na ronda de internação e ajustar temperatura/umidade da gaiola."
        elif recs and recs[0].publico == "tutor":
            acao = f"Oferecer ao tutor: {recs[0].servico}."
        elif recs:
            acao = f"Pedir à equipe: {recs[0].servico}."
        else:
            acao = "Manter acompanhamento de rotina."

        insight = InsightPet(
            pet=pet,
            score_risco=min(score, 100),
            nivel_risco=nivel,
            faixa_conforto=faixa,
            internado=internado,
            alertas=alertas,
            recomendacoes=recs,
            acao_priorizada=acao,
            leitura=leitura,
        )
        pront = next((p for p in self.prontuarios if p.get("id_pet") == pet.id_pet), None)
        meds = [m for m in self.medicamentos if m["id_pet"] == pet.id_pet and m.get("em_uso")]
        (
            insight.mensagem_tutor,
            insight.resumo_clinico,
            insight.prompt_tutor,
            insight.prompt_veterinario,
        ) = ia_generativa.gerar_textos(pet, insight, pront, meds)
        return insight

    def fila_prioridade(self) -> list[InsightPet]:
        insights = [self.analisar_pet(p.id_pet) for p in self.pets]
        ordem = {"critico": 0, "alto": 1, "medio": 2, "baixo": 3}
        return sorted(insights, key=lambda i: (ordem[i.nivel_risco], -i.score_risco, i.pet.nome))
