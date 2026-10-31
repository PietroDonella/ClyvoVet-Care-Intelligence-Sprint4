"""Validação da base clínica e das leituras IoT antes de alimentar a IA."""

from __future__ import annotations

from datetime import datetime

STATUS_CONSULTA = {"Agendada", "Realizada", "Cancelada"}
STATUS_VACINA = {"Em dia", "Vencida", "Reforco pendente"}


class DadosInvalidos(ValueError):
    def __init__(self, erros: list[str]):
        super().__init__("; ".join(erros))
        self.erros = erros


def _data_ok(valor: str) -> bool:
    try:
        datetime.fromisoformat(valor)
    except (TypeError, ValueError):
        return False
    return True


def validar_base(clinica: dict, leituras: list[dict]) -> list[str]:
    erros: list[str] = []
    tutores = clinica.get("tutores") or []
    pets = clinica.get("pets") or []
    ids_tutores = {t.get("id_tutor") for t in tutores}
    ids_pets: set[int] = set()
    rfids: set[str] = set()

    if not tutores:
        erros.append("A base não tem tutores.")
    if not pets:
        erros.append("A base não tem pets.")

    for tutor in tutores:
        if not tutor.get("nome"):
            erros.append(f"Tutor {tutor.get('id_tutor')} sem nome.")

    for pet in pets:
        id_pet = pet.get("id_pet")
        if id_pet in ids_pets:
            erros.append(f"id_pet duplicado: {id_pet}.")
        ids_pets.add(id_pet)
        if pet.get("id_tutor") not in ids_tutores:
            erros.append(f"{pet.get('nome')} aponta para um tutor inexistente.")
        rfid = str(pet.get("rfid_uid") or "").strip()
        if not rfid:
            erros.append(f"{pet.get('nome')} está sem RFID.")
        elif rfid.upper() in rfids:
            erros.append(f"RFID duplicado: {rfid}.")
        else:
            rfids.add(rfid.upper())
        if pet.get("idade") is None or pet.get("peso") is None:
            erros.append(f"{pet.get('nome')} está sem idade ou peso.")

    for consulta in clinica.get("consultas") or []:
        if consulta.get("id_pet") not in ids_pets:
            erros.append(f"Consulta {consulta.get('id_consulta')} sem pet válido.")
        if consulta.get("status") not in STATUS_CONSULTA:
            erros.append(
                f"Consulta {consulta.get('id_consulta')} com status desconhecido."
            )
        if not _data_ok(consulta.get("data_consulta")):
            erros.append(f"Consulta {consulta.get('id_consulta')} com data inválida.")

    for prontuario in clinica.get("prontuarios") or []:
        if prontuario.get("id_pet") not in ids_pets:
            erros.append(f"Prontuário {prontuario.get('id_prontuario')} sem pet válido.")
        if not str(prontuario.get("diagnostico") or "").strip():
            erros.append(f"Prontuário {prontuario.get('id_prontuario')} sem diagnóstico.")

    for vacina in clinica.get("vacinas") or []:
        if vacina.get("id_pet") not in ids_pets:
            erros.append(f"Vacina {vacina.get('nome')} sem pet válido.")
        if vacina.get("status") not in STATUS_VACINA:
            erros.append(f"Vacina {vacina.get('nome')} com status desconhecido.")

    for medicamento in clinica.get("medicamentos") or []:
        if medicamento.get("id_pet") not in ids_pets:
            erros.append(f"Medicamento {medicamento.get('nome')} sem pet válido.")

    for indice, leitura in enumerate(leituras, start=1):
        erros.extend(f"Leitura {indice}: {msg}" for msg in validar_leitura(leitura, ids_pets))
    return erros


def validar_leitura(bruta: dict, ids_pets: set[int]) -> list[str]:
    erros: list[str] = []
    obrigatorios = (
        "timestamp",
        "origem",
        "topico",
        "gaiola",
        "temperatura",
        "umidade",
        "rfid_lido",
        "pet_esperado_id",
    )
    if not isinstance(bruta, dict):
        return ["O corpo da leitura precisa ser um objeto JSON."]
    faltando = [campo for campo in obrigatorios if campo not in bruta]
    if faltando:
        return ["Campos ausentes: " + ", ".join(faltando) + "."]

    if not _data_ok(bruta.get("timestamp")):
        erros.append("timestamp inválido.")
    if not str(bruta.get("origem") or "").strip():
        erros.append("origem vazia.")
    topico = str(bruta.get("topico") or "")
    if not topico.startswith("clyvovet/"):
        erros.append("tópico precisa começar com clyvovet/.")
    if not str(bruta.get("gaiola") or "").strip():
        erros.append("gaiola vazia.")
    if not str(bruta.get("rfid_lido") or "").strip():
        erros.append("RFID lido vazio.")

    erros.extend(_numero(bruta.get("temperatura"), "temperatura", 0, 50))
    erros.extend(_numero(bruta.get("umidade"), "umidade", 0, 100))

    pet_id = bruta.get("pet_esperado_id")
    if isinstance(pet_id, bool) or not isinstance(pet_id, int):
        erros.append("pet_esperado_id precisa ser inteiro.")
    elif pet_id not in ids_pets:
        erros.append(f"pet {pet_id} não está na base.")
    return erros


def _numero(valor, nome: str, minimo: float, maximo: float) -> list[str]:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return [f"{nome} precisa ser numérico."]
    if not minimo <= float(valor) <= maximo:
        return [f"{nome} fora da faixa {minimo:g}–{maximo:g}."]
    return []
