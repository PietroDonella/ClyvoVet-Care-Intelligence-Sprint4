"""Camada generativa condicionada ao JSON de contexto e aos prompts versionados.

Os arquivos em `prompts/` são os mesmos que iriam para um LLM. Aqui o texto
é montado no próprio processo, a partir desse contexto, para a demo rodar
sem chave, sem alucinar dose e com a mesma frase toda vez que o professor
repetir o caso.
"""

from __future__ import annotations

import json
from pathlib import Path

from .modelos import InsightPet, Pet, Recomendacao
from .motor_regras import faixa_etaria

PASTA_PROMPTS = Path(__file__).resolve().parents[2] / "prompts"
CODIGOS_OCULTOS_DO_TUTOR = {"RFID_TROCA_PACIENTE", "RFID_DESCONHECIDO"}


def preencher_prompt(nome_arquivo: str, contexto: dict) -> str:
    modelo = (PASTA_PROMPTS / nome_arquivo).read_text(encoding="utf-8")
    bloco = json.dumps(contexto, ensure_ascii=False, indent=2)
    return modelo.replace("{{contexto}}", bloco)


def motivo_para_tutor(rec: Recomendacao) -> str:
    if "identidade" in rec.servico.lower():
        return "A equipe confirma a coleira antes de qualquer cuidado."
    return rec.motivo


def selecionar_para_tutor(recomendacoes: list[Recomendacao]) -> list[Recomendacao]:
    do_tutor = [r for r in recomendacoes if r.publico == "tutor"]
    if not do_tutor:
        do_tutor = list(recomendacoes[:2])
    return do_tutor[:3]


def contexto_llm(pet: Pet, insight: InsightPet, prontuario: dict | None, meds: list[dict]) -> dict:
    return {
        "pet": {
            "id_pet": pet.id_pet,
            "nome": pet.nome,
            "especie": pet.especie,
            "idade": pet.idade,
            "peso": pet.peso,
            "faixa_etaria": faixa_etaria(pet),
            "comportamento": pet.comportamento,
            "gaiola": pet.gaiola,
            "status_internacao": pet.status_internacao,
        },
        "tutor": {"nome": pet.tutor_nome, "telefone": pet.tutor_telefone},
        "faixa_conforto": insight.faixa_conforto,
        "nivel_risco": insight.nivel_risco,
        "score_risco": insight.score_risco,
        "acao_priorizada": insight.acao_priorizada,
        "alertas": [a.__dict__ for a in insight.alertas],
        "recomendacoes": [r.__dict__ for r in insight.recomendacoes],
        "prontuario": prontuario,
        "medicamentos_em_uso": meds,
    }


def mensagem_tutor(pet: Pet, insight: InsightPet) -> str:
    etapa = faixa_etaria(pet)
    tutor = pet.tutor_nome.split()[0] if pet.tutor_nome else "tutor"

    if insight.nivel_risco == "critico":
        abertura = (
            f"Olá, {tutor}. Identificamos um alerta de segurança envolvendo {pet.nome} "
            "na internação da CLYVO VET e a equipe já foi acionada."
        )
    elif insight.nivel_risco == "alto":
        abertura = (
            f"Olá, {tutor}. O acompanhamento de {pet.nome} na CLYVO VET gerou um alerta "
            "de prioridade alta, pensado no conforto e na segurança dele."
        )
    else:
        abertura = (
            f"Olá, {tutor}. Segue um resumo personalizado do cuidado de {pet.nome} "
            f"({pet.especie.lower()} {etapa}, {pet.idade} ano(s))."
        )

    if any(a.codigo in CODIGOS_OCULTOS_DO_TUTOR for a in insight.alertas):
        texto_alertas = (
            f"A equipe está conferindo a identificação de {pet.nome} na internação "
            "antes de qualquer procedimento."
        )
    else:
        visiveis = [a for a in insight.alertas if a.codigo not in CODIGOS_OCULTOS_DO_TUTOR]
        if visiveis:
            texto_alertas = " ".join(a.detalhe for a in visiveis[:2])
        else:
            texto_alertas = "Nenhum alerta ambiental crítico no momento."

    recs = selecionar_para_tutor(insight.recomendacoes)
    if recs:
        proximos = " ".join(
            f"{i + 1}) {r.servico} — {motivo_para_tutor(r)}" for i, r in enumerate(recs)
        )
    else:
        proximos = "Manter o calendário de consultas em dia já é suficiente nesta etapa."

    fechamento = (
        "Esta mensagem é um apoio à jornada de cuidado: a conduta clínica continua "
        "com o veterinário responsável. Responda pelo app se quiser agendar o próximo passo."
    )
    return f"{abertura} {texto_alertas} Próximas ações sugeridas: {proximos} {fechamento}"


def resumo_clinico(pet: Pet, insight: InsightPet, prontuario: dict | None, meds: list[dict]) -> str:
    diagnostico = prontuario["diagnostico"] if prontuario else "Sem prontuário recente."
    med_txt = ", ".join(f"{m['nome']} ({m['indicacao']})" for m in meds) or "nenhum em uso"
    alertas = "; ".join(f"[{a.nivel}] {a.titulo}" for a in insight.alertas) or "sem alertas IoT"
    recs = "; ".join(r.servico for r in insight.recomendacoes[:4]) or "nenhuma"
    return (
        f"Paciente {pet.nome} (id {pet.id_pet}, {pet.especie}, {pet.idade}a, {pet.peso} kg). "
        f"RFID {pet.rfid_uid}. Internação: {pet.status_internacao or 'ambulatorial'}"
        f"{f' / gaiola {pet.gaiola}' if pet.gaiola else ''}. "
        f"Comportamento: {pet.comportamento} "
        f"Último diagnóstico: {diagnostico} "
        f"Medicação: {med_txt}. "
        f"Risco {insight.nivel_risco} (score {insight.score_risco}). "
        f"Alertas: {alertas}. "
        f"Ação priorizada: {insight.acao_priorizada}. "
        f"Serviços sugeridos: {recs}. "
        "A decisão terapêutica permanece com o veterinário responsável."
    )


def gerar_textos(
    pet: Pet,
    insight: InsightPet,
    prontuario: dict | None,
    meds: list[dict],
) -> tuple[str, str, str, str]:
    contexto = contexto_llm(pet, insight, prontuario, meds)
    prompt_tutor = preencher_prompt("sistema_tutor.txt", contexto)
    prompt_vet = preencher_prompt("sistema_veterinario.txt", contexto)
    return (
        mensagem_tutor(pet, insight),
        resumo_clinico(pet, insight, prontuario, meds),
        prompt_tutor,
        prompt_vet,
    )
