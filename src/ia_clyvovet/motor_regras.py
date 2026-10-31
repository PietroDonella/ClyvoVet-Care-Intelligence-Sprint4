"""Motor de regras para triagem térmica e identificação RFID.

Estresse térmico e troca de paciente não passam por LLM. A saída é
determinística: o mesmo dado produz o mesmo alerta, e o código explica
o motivo. Erro aqui pode significar medicação no animal errado.
"""

from __future__ import annotations

from .modelos import Alerta, LeituraIoT, Pet


def faixa_etaria(pet: Pet) -> str:
    if pet.idade < 2:
        return "filhote"
    if pet.idade >= 8:
        return "senior"
    return "adulto"


def faixa_conforto(pet: Pet) -> tuple[float, float, float, float, str]:
    """Retorna (t_min, t_max, u_min, u_max, descricao)."""
    etapa = faixa_etaria(pet)
    if pet.especie.lower().startswith("gato"):
        faixas = {
            "filhote": (22.0, 28.0, 40.0, 65.0),
            "adulto": (20.0, 27.0, 40.0, 70.0),
            "senior": (20.0, 26.0, 40.0, 65.0),
        }
    else:
        faixas = {
            "filhote": (20.0, 26.0, 40.0, 70.0),
            "adulto": (18.0, 26.0, 40.0, 70.0),
            "senior": (20.0, 25.0, 40.0, 65.0),
        }
    t_min, t_max, u_min, u_max = faixas[etapa]
    descricao = (
        f"{pet.especie} {etapa}: {t_min:.0f}–{t_max:.0f} °C, "
        f"umidade {u_min:.0f}–{u_max:.0f}%"
    )
    return t_min, t_max, u_min, u_max, descricao


def avaliar_ambiente(pet: Pet, leitura: LeituraIoT) -> tuple[int, list[Alerta]]:
    t_min, t_max, u_min, u_max, _ = faixa_conforto(pet)
    score = 0
    alertas: list[Alerta] = []

    desvio_temp = 0.0
    if leitura.temperatura < t_min:
        desvio_temp = t_min - leitura.temperatura
        tipo = "frio"
    elif leitura.temperatura > t_max:
        desvio_temp = leitura.temperatura - t_max
        tipo = "calor"
    else:
        tipo = "ok"

    if desvio_temp >= 3:
        score += 45
        nivel = "alto"
    elif desvio_temp >= 1:
        score += 25
        nivel = "medio"
    else:
        nivel = "baixo"

    if tipo != "ok":
        alertas.append(
            Alerta(
                codigo="IOT_TERMICO",
                nivel=nivel,
                titulo=f"Estresse térmico por {tipo}",
                detalhe=(
                    f"Gaiola {leitura.gaiola}: {leitura.temperatura:.1f} °C "
                    f"(faixa segura {t_min:.0f}–{t_max:.0f} °C para {pet.nome})."
                ),
            )
        )

    if leitura.umidade < u_min or leitura.umidade > u_max:
        score += 15
        alertas.append(
            Alerta(
                codigo="IOT_UMIDADE",
                nivel="medio",
                titulo="Umidade fora da faixa",
                detalhe=(
                    f"Umidade {leitura.umidade:.0f}% na gaiola {leitura.gaiola} "
                    f"(ideal {u_min:.0f}–{u_max:.0f}%)."
                ),
            )
        )

    etapa = faixa_etaria(pet)
    if etapa in {"filhote", "senior"} and desvio_temp >= 1:
        score += 15
        alertas.append(
            Alerta(
                codigo="PERFIL_VULNERAVEL",
                nivel="alto" if etapa == "filhote" and pet.peso < 2 else "medio",
                titulo=f"Pet {etapa} mais sensível ao clima",
                detalhe=(
                    f"{pet.nome} é {etapa} ({pet.idade} ano(s), {pet.peso} kg). "
                    "O desvio climático recebe peso extra na priorização."
                ),
            )
        )

    return min(score, 100), alertas


def avaliar_identificacao(
    pet_esperado: Pet,
    pets_por_rfid: dict[str, Pet],
    leitura: LeituraIoT,
) -> list[Alerta]:
    """RFID divergente ou desconhecido trava a fila. Os dois são segurança do paciente."""
    pet_lido = pets_por_rfid.get(leitura.rfid_lido.upper())
    if pet_lido is None:
        return [
            Alerta(
                codigo="RFID_DESCONHECIDO",
                nivel="critico",
                titulo="Tag RFID não cadastrada",
                detalhe=(
                    f"UID {leitura.rfid_lido} lido na gaiola {leitura.gaiola} "
                    "não existe na base. Interromper o procedimento até identificar o animal."
                ),
            )
        ]

    if pet_lido.id_pet != pet_esperado.id_pet:
        return [
            Alerta(
                codigo="RFID_TROCA_PACIENTE",
                nivel="critico",
                titulo="Risco de troca de paciente",
                detalhe=(
                    f"Gaiola {leitura.gaiola} está alocada para {pet_esperado.nome} "
                    f"(RFID {pet_esperado.rfid_uid}), mas a tag lida pertence a "
                    f"{pet_lido.nome} (RFID {pet_lido.rfid_uid}). "
                    "Bloquear medicação e conferir a coleira antes de qualquer procedimento."
                ),
            )
        ]
    return []


def nivel_de_score(score: int, tem_critico: bool) -> str:
    if tem_critico:
        return "critico"
    if score >= 50:
        return "alto"
    if score >= 25:
        return "medio"
    return "baixo"
