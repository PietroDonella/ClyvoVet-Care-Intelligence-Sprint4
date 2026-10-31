"""Converte o JSON da API .NET da CLYVO VET na base que a IA consome.

Rotas já existentes na aplicação:
- GET /api/tutores
- GET /api/animais
- GET /api/consultas
- GET /api/prontuarios

A entidade Pet da API não tem RFID, gaiola nem internação. A entidade
Prontuario não tem id do pet: o vínculo chega pela consulta. Vacina,
medicação, comportamento e coleira continuam na base local e entram
pelo id.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from .validacao import DadosInvalidos


class ClienteApiError(RuntimeError):
    pass


def campo(obj: dict, *nomes: str, obrigatorio: bool = True):
    for nome in nomes:
        if nome in obj and obj[nome] is not None:
            return obj[nome]
    if obrigatorio:
        raise DadosInvalidos([f"Campo ausente na API: {nomes[0]}."])
    return None


def _data_curta(valor) -> str | None:
    if valor is None:
        return None
    return str(valor)[:10]


def _inteiro(valor, nome: str) -> int:
    if isinstance(valor, bool):
        raise DadosInvalidos([f"{nome} inválido na API."])
    if isinstance(valor, int):
        return valor
    if isinstance(valor, float) and valor.is_integer():
        return int(valor)
    if isinstance(valor, str) and valor.lstrip("-").isdigit():
        return int(valor)
    raise DadosInvalidos([f"{nome} inválido na API."])


def _decimal(valor, nome: str) -> float:
    if isinstance(valor, bool) or valor is None:
        raise DadosInvalidos([f"{nome} ausente na API."])
    try:
        return float(valor)
    except (TypeError, ValueError) as exc:
        raise DadosInvalidos([f"{nome} inválido na API."]) from exc


def mesclar_com_api(base_local: dict, api: dict) -> dict:
    pets_api = api.get("pets") or []
    tutores_api = api.get("tutores") or []
    consultas_api = api.get("consultas") or []
    prontuarios_api = api.get("prontuarios") or []
    if not pets_api or not tutores_api:
        raise DadosInvalidos(["A API não devolveu tutores e pets."])

    pets_locais = {p["id_pet"]: p for p in base_local["pets"]}
    pets = []
    ids_vistos: set[int] = set()
    for bruto in pets_api:
        id_pet = _inteiro(campo(bruto, "id", "Id"), "id do pet")
        local = pets_locais.get(id_pet, {})
        idade = campo(bruto, "idade", "Idade", obrigatorio=False)
        if idade is None:
            idade = local.get("idade")
        peso = campo(bruto, "peso", "Peso", obrigatorio=False)
        if peso is None:
            peso = local.get("peso")
        pets.append(
            {
                "id_pet": id_pet,
                "id_tutor": _inteiro(campo(bruto, "idTutor", "IdTutor"), "idTutor"),
                "nome": campo(bruto, "nome", "Nome"),
                "especie": campo(bruto, "especie", "Especie"),
                "cor": campo(bruto, "cor", "Cor", obrigatorio=False) or local.get("cor") or "",
                "idade": _inteiro(idade, "idade"),
                "peso": _decimal(peso, "peso"),
                "rfid_uid": local.get("rfid_uid", ""),
                "status_internacao": local.get("status_internacao"),
                "gaiola": local.get("gaiola"),
                "comportamento": local.get("comportamento", ""),
            }
        )
        ids_vistos.add(id_pet)

    for pet in base_local["pets"]:
        if pet["id_pet"] not in ids_vistos:
            pets.append(pet)

    tutores = []
    for bruto in tutores_api:
        tutores.append(
            {
                "id_tutor": _inteiro(campo(bruto, "id", "Id"), "id do tutor"),
                "nome": campo(bruto, "nome", "Nome"),
                "cpf": campo(bruto, "cpf", "Cpf", obrigatorio=False) or "",
                "telefone": campo(bruto, "telefone", "Telefone", obrigatorio=False) or "",
            }
        )

    prontuario_por_id = {}
    for bruto in prontuarios_api:
        id_prontuario = _inteiro(campo(bruto, "id", "Id"), "id do prontuário")
        prontuario_por_id[id_prontuario] = bruto

    consultas = []
    prontuarios = []
    prontuarios_vistos: set[int] = set()
    for bruto in consultas_api:
        id_prontuario = campo(bruto, "idProntuario", "IdProntuario", obrigatorio=False)
        if id_prontuario is not None:
            id_prontuario = _inteiro(id_prontuario, "idProntuario")
        id_pet = _inteiro(campo(bruto, "idPet", "IdPet"), "idPet")
        consultas.append(
            {
                "id_consulta": _inteiro(campo(bruto, "id", "Id"), "id da consulta"),
                "id_veterinario": _inteiro(
                    campo(bruto, "idVeterinario", "IdVeterinario"),
                    "idVeterinario",
                ),
                "id_pet": id_pet,
                "id_clinica": _inteiro(campo(bruto, "idClinica", "IdClinica"), "idClinica"),
                "id_prontuario": id_prontuario,
                "data_consulta": _data_curta(campo(bruto, "dataConsulta", "DataConsulta")),
                "status": campo(bruto, "status", "Status"),
            }
        )
        if id_prontuario in prontuario_por_id and id_prontuario not in prontuarios_vistos:
            origem = prontuario_por_id[id_prontuario]
            prontuarios.append(
                {
                    "id_prontuario": id_prontuario,
                    "id_pet": id_pet,
                    "diagnostico": campo(origem, "diagnostico", "Diagnostico", obrigatorio=False) or "",
                    "data_registro": _data_curta(
                        campo(origem, "dataRegistro", "DataRegistro", obrigatorio=False)
                    )
                    or "1970-01-01",
                }
            )
            prontuarios_vistos.add(id_prontuario)

    return {
        "tutores": tutores,
        "pets": pets,
        "prontuarios": prontuarios,
        "consultas": consultas,
        "vacinas": base_local["vacinas"],
        "medicamentos": base_local["medicamentos"],
    }


def buscar_json(url: str, timeout: float = 8) -> list:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resposta:
            corpo = json.loads(resposta.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise ClienteApiError(f"Não foi possível ler {url}: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise ClienteApiError(f"A resposta de {url} não é JSON.") from exc
    if not isinstance(corpo, list):
        raise ClienteApiError(f"A resposta de {url} precisa ser uma lista.")
    return corpo


def carregar_api(base_url: str) -> dict:
    raiz = base_url.rstrip("/")
    return {
        "tutores": buscar_json(raiz + "/api/tutores"),
        "pets": buscar_json(raiz + "/api/animais"),
        "consultas": buscar_json(raiz + "/api/consultas"),
        "prontuarios": buscar_json(raiz + "/api/prontuarios"),
    }
