"""Quadro de personalização e fila, usado pelo terminal e pela documentação."""

from __future__ import annotations

from .modelos import LeituraIoT, Pet
from .motor_regras import avaliar_ambiente, faixa_conforto, faixa_etaria, nivel_de_score
from .orquestrador import CareIntelligence


def _perfil(nome: str, especie: str, idade: int, peso: float) -> Pet:
    return Pet(
        id_pet=0,
        id_tutor=0,
        nome=nome,
        especie=especie,
        cor="",
        idade=idade,
        peso=peso,
        rfid_uid="PERFIL",
        status_internacao=None,
        gaiola=None,
        comportamento="",
    )


PERFIS = (
    _perfil("cão adulto", "Cachorro", 5, 15.0),
    _perfil("cão sênior", "Cachorro", 8, 25.0),
    _perfil("gato adulto", "Gato", 3, 5.0),
    _perfil("gato filhote", "Gato", 1, 1.2),
)


def quadro_personalizacao(temperatura: float, umidade: float = 55.0) -> list[dict]:
    leitura = LeituraIoT(
        timestamp="2026-09-11T10:00:00",
        origem="avaliacao",
        topico="clyvovet/internacao/temp",
        gaiola="G-00",
        temperatura=temperatura,
        umidade=umidade,
        rfid_lido="PERFIL",
        pet_esperado_id=0,
    )
    linhas = []
    for pet in PERFIS:
        score, alertas = avaliar_ambiente(pet, leitura)
        linhas.append(
            {
                "perfil": f"{pet.especie} {faixa_etaria(pet)}",
                "peso_kg": pet.peso,
                "faixa": faixa_conforto(pet)[4],
                "score": score,
                "nivel": nivel_de_score(score, False),
                "alertas": [a.codigo for a in alertas],
            }
        )
    return linhas


def texto_relatorio(ia: CareIntelligence) -> str:
    linhas = [
        "CLYVO VET — avaliação da Care Intelligence (4ª sprint)",
        "",
        (
            f"Base validada: {len(ia.tutores)} tutores, {len(ia.pets)} pets, "
            f"{len(ia.leituras)} leituras IoT."
        ),
        "Data de referência das recomendações: 2026-09-11.",
        "",
        "Mesma sala, perfis diferentes.",
        "Leitura 27,0 °C e 55% de umidade:",
    ]
    for item in quadro_personalizacao(27.0):
        linhas.append(
            f"  {item['perfil']:<22} score {item['score']:>3}  {item['nivel']:<8}  {item['faixa']}"
        )
    linhas.append("Leitura 21,0 °C e 55% de umidade:")
    for item in quadro_personalizacao(21.0):
        linhas.append(
            f"  {item['perfil']:<22} score {item['score']:>3}  {item['nivel']:<8}  {item['faixa']}"
        )
    linhas.extend(["", "Fila do plantão com as leituras da base:", ""])
    for posicao, insight in enumerate(ia.fila_prioridade(), start=1):
        pet = insight.pet
        lugar = pet.gaiola or "ambulatorial"
        linhas.append(
            f"  {posicao}. {pet.nome:<10} {insight.nivel_risco:<8} {insight.score_risco:>3}  "
            f"{lugar:<12}  {insight.acao_priorizada}"
        )
    linhas.extend(
        [
            "",
            "A conduta clínica permanece com o veterinário responsável.",
        ]
    )
    return "\n".join(linhas) + "\n"
