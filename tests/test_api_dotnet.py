import json
import unittest

import suporte
from ia_clyvovet.cliente_api import mesclar_com_api
from ia_clyvovet.orquestrador import CareIntelligence


def api_da_base(base):
    return {
        "tutores": [
            {
                "id": tutor["id_tutor"],
                "nome": tutor["nome"],
                "cpf": tutor["cpf"],
                "telefone": tutor["telefone"],
            }
            for tutor in base["tutores"]
        ],
        "pets": [
            {
                "id": pet["id_pet"],
                "idTutor": pet["id_tutor"],
                "nome": pet["nome"],
                "especie": pet["especie"],
                "cor": pet["cor"],
                "idade": pet["idade"],
                "peso": pet["peso"],
            }
            for pet in base["pets"]
        ],
        "consultas": [
            {
                "id": consulta["id_consulta"],
                "idVeterinario": consulta["id_veterinario"],
                "idPet": consulta["id_pet"],
                "idClinica": consulta["id_clinica"],
                "idProntuario": consulta["id_prontuario"],
                "dataConsulta": consulta["data_consulta"] + "T00:00:00",
                "status": consulta["status"],
            }
            for consulta in base["consultas"]
        ],
        "prontuarios": [
            {
                "id": prontuario["id_prontuario"],
                "diagnostico": prontuario["diagnostico"],
                "dataRegistro": prontuario["data_registro"] + "T00:00:00",
            }
            for prontuario in base["prontuarios"]
        ],
    }


class TestApiDotNet(unittest.TestCase):
    def setUp(self):
        self.base = json.loads(
            (suporte.ROOT / "data" / "base_clinica.json").read_text(encoding="utf-8")
        )

    def test_nome_vem_da_api_e_rfid_fica_na_extensao_local(self):
        api = api_da_base(self.base)
        for pet in api["pets"]:
            if pet["id"] == 3:
                pet["nome"] = "Thor da API"
        mesclada = mesclar_com_api(self.base, api)
        thor = next(pet for pet in mesclada["pets"] if pet["id_pet"] == 3)
        self.assertEqual(thor["nome"], "Thor da API")
        self.assertEqual(thor["rfid_uid"], "C3D4E5F6")
        self.assertEqual(thor["gaiola"], "G-04")
        ia = CareIntelligence(suporte.ROOT / "data", clinica=mesclada)
        insight = ia.analisar_pet(3)
        self.assertEqual(insight.pet.nome, "Thor da API")
        self.assertEqual(insight.nivel_risco, "alto")
        servicos = {rec.servico for rec in insight.recomendacoes}
        self.assertIn("Reavaliação otológica", servicos)

    def test_aceita_pascal_case_do_serializador(self):
        api = api_da_base(self.base)
        primeiro = api["pets"][0]
        api["pets"][0] = {
            "Id": primeiro["id"],
            "IdTutor": primeiro["idTutor"],
            "Nome": "Rex Pascal",
            "Especie": primeiro["especie"],
            "Cor": primeiro["cor"],
            "Idade": primeiro["idade"],
            "Peso": primeiro["peso"],
        }
        mesclada = mesclar_com_api(self.base, api)
        rex = next(pet for pet in mesclada["pets"] if pet["id_pet"] == primeiro["id"])
        self.assertEqual(rex["nome"], "Rex Pascal")
        self.assertTrue(rex["rfid_uid"])


if __name__ == "__main__":
    unittest.main()
