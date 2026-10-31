import json
import unittest

import suporte
from ia_clyvovet.modelos import LeituraIoT, Pet
from ia_clyvovet.motor_regras import (
    avaliar_ambiente,
    avaliar_identificacao,
    nivel_de_score,
)
from ia_clyvovet.avaliacao import quadro_personalizacao
from ia_clyvovet.validacao import validar_base, validar_leitura


def _pet(nome="Thor", especie="Cachorro", idade=8, peso=25.0, id_pet=3, rfid="C3D4E5F6"):
    return Pet(
        id_pet=id_pet,
        id_tutor=1,
        nome=nome,
        especie=especie,
        cor="",
        idade=idade,
        peso=peso,
        rfid_uid=rfid,
        status_internacao="Internado",
        gaiola="G-04",
        comportamento="",
    )


def _leitura(temperatura=24.0, umidade=55.0, rfid="C3D4E5F6", pet_id=3):
    return LeituraIoT(
        timestamp="2026-09-11T10:00:00",
        origem="teste",
        topico="clyvovet/internacao/temp",
        gaiola="G-04",
        temperatura=temperatura,
        umidade=umidade,
        rfid_lido=rfid,
        pet_esperado_id=pet_id,
    )


class TestRegras(unittest.TestCase):
    def test_mesma_temperatura_muda_com_o_perfil(self):
        scores_27 = [item["score"] for item in quadro_personalizacao(27.0)]
        scores_21 = [item["score"] for item in quadro_personalizacao(21.0)]
        self.assertEqual(scores_27, [25, 40, 0, 0])
        self.assertEqual(scores_21, [0, 0, 0, 40])

    def test_limites_de_nivel(self):
        self.assertEqual(nivel_de_score(24, False), "baixo")
        self.assertEqual(nivel_de_score(25, False), "medio")
        self.assertEqual(nivel_de_score(49, False), "medio")
        self.assertEqual(nivel_de_score(50, False), "alto")
        self.assertEqual(nivel_de_score(0, True), "critico")

    def test_rfid_trocado_e_desconhecido_sao_criticos(self):
        thor = _pet()
        rex = _pet(nome="Rex", id_pet=1, rfid="A1B2C3D4")
        mapa = {thor.rfid_uid: thor, rex.rfid_uid: rex}
        troca = avaliar_identificacao(thor, mapa, _leitura(rfid="A1B2C3D4"))
        desconhecido = avaliar_identificacao(thor, mapa, _leitura(rfid="ZZZZZZZZ"))
        certo = avaliar_identificacao(thor, mapa, _leitura(rfid="C3D4E5F6"))
        self.assertEqual(troca[0].codigo, "RFID_TROCA_PACIENTE")
        self.assertEqual(troca[0].nivel, "critico")
        self.assertEqual(desconhecido[0].codigo, "RFID_DESCONHECIDO")
        self.assertEqual(desconhecido[0].nivel, "critico")
        self.assertEqual(certo, [])

    def test_calor_de_senior_pontua_acima_de_adulto(self):
        senior = _pet(idade=8)
        adulto = _pet(nome="Rex", idade=5, id_pet=1)
        leitura = _leitura(temperatura=32.4, umidade=50)
        score_senior, _ = avaliar_ambiente(senior, leitura)
        score_adulto, _ = avaliar_ambiente(adulto, leitura)
        self.assertGreater(score_senior, score_adulto)

    def test_base_da_sprint_passa_na_validacao(self):
        clinica = json.loads((suporte.ROOT / "data" / "base_clinica.json").read_text(encoding="utf-8"))
        iot = json.loads((suporte.ROOT / "data" / "leituras_iot.json").read_text(encoding="utf-8"))
        self.assertEqual(validar_base(clinica, iot["leituras"]), [])

    def test_temperatura_absurda_e_recusada(self):
        erros = validar_leitura(
            {
                "timestamp": "2026-10-30T15:00:00",
                "origem": "teste",
                "topico": "clyvovet/internacao/temp",
                "gaiola": "G-04",
                "temperatura": 80,
                "umidade": 50,
                "rfid_lido": "C3D4E5F6",
                "pet_esperado_id": 3,
            },
            {3},
        )
        self.assertTrue(erros)
        self.assertTrue(any("temperatura" in erro for erro in erros))


if __name__ == "__main__":
    unittest.main()
