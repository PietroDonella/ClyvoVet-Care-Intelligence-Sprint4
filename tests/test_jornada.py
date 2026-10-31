import unittest

import suporte
from ia_clyvovet.avaliacao import texto_relatorio
from ia_clyvovet.ia_generativa import preencher_prompt
from ia_clyvovet.modelos import Pet
from ia_clyvovet.orquestrador import CareIntelligence
from ia_clyvovet.recomendador import recomendar
from ia_clyvovet.servico_http import Aplicacao
from ia_clyvovet.validacao import DadosInvalidos


def leitura_thor(temperatura, umidade, rfid, timestamp="2026-09-11T12:00:00"):
    return {
        "timestamp": timestamp,
        "origem": "teste",
        "topico": "clyvovet/internacao/temp",
        "gaiola": "G-04",
        "temperatura": temperatura,
        "umidade": umidade,
        "rfid_lido": rfid,
        "pet_esperado_id": 3,
    }


class TestJornada(unittest.TestCase):
    def setUp(self):
        self.ia = CareIntelligence(suporte.ROOT / "data")

    def test_fila_comeca_pelo_bidu_e_separa_os_internados(self):
        nomes = [item.pet.nome for item in self.ia.fila_prioridade()]
        self.assertEqual(
            nomes,
            ["Bidu", "Pipoca", "Thor", "Frajola", "Luna", "Mia", "Nina", "Rex"],
        )
        bidu = self.ia.analisar_pet(7)
        thor = self.ia.analisar_pet(3)
        pipoca = self.ia.analisar_pet(8)
        self.assertEqual(bidu.nivel_risco, "critico")
        self.assertEqual(bidu.score_risco, 90)
        self.assertEqual(thor.nivel_risco, "alto")
        self.assertEqual(thor.score_risco, 75)
        self.assertEqual(pipoca.nivel_risco, "alto")
        self.assertEqual(pipoca.score_risco, 75)

    def test_thor_recebe_vacina_otite_clima_e_checkup(self):
        servicos = {rec.servico for rec in self.ia.analisar_pet(3).recomendacoes}
        self.assertIn("Vacinação / atualização de protocolo", servicos)
        self.assertIn("Reavaliação otológica", servicos)
        self.assertIn("Ajuste imediato do microclima da gaiola", servicos)
        self.assertIn("Check-up geriátrico periódico", servicos)
        self.assertIn("Conferência de medicação em uso", servicos)

    def test_pipoca_recebe_frio_reforco_e_protocolo_de_filhote(self):
        servicos = {rec.servico for rec in self.ia.analisar_pet(8).recomendacoes}
        self.assertIn("Retorno para reforço vacinal", servicos)
        self.assertIn("Protocolo de filhote (vacina + vermífugo + socialização)", servicos)
        self.assertIn("Ajuste imediato do microclima da gaiola", servicos)

    def test_leitura_nova_dentro_da_faixa_baixa_o_risco_do_thor(self):
        self.ia.registrar_leitura(leitura_thor(22, 50, "C3D4E5F6"))
        insight = self.ia.analisar_pet(3)
        self.assertEqual(insight.score_risco, 0)
        self.assertEqual(insight.nivel_risco, "baixo")
        self.assertTrue(any("Vacinação" in rec.servico for rec in insight.recomendacoes))

    def test_leitura_invalida_nao_altera_o_caso(self):
        antes = self.ia.analisar_pet(3).score_risco
        with self.assertRaises(DadosInvalidos):
            self.ia.registrar_leitura(leitura_thor(80, 50, "C3D4E5F6"))
        self.assertEqual(self.ia.analisar_pet(3).score_risco, antes)
        self.assertEqual(len(self.ia.leituras), 3)

    def test_tutor_nao_ve_o_nome_do_outro_animal(self):
        bidu = self.ia.analisar_pet(7)
        self.assertIn("Bidu", bidu.mensagem_tutor)
        self.assertNotIn("Rex", bidu.mensagem_tutor)
        self.assertNotIn("RFID", bidu.mensagem_tutor)
        self.assertIn("veterinário", bidu.mensagem_tutor)
        self.assertTrue(any("Rex" in alerta.detalhe for alerta in bidu.alertas))
        self.assertIn("decisão terapêutica", bidu.resumo_clinico)
        self.assertNotIn("mg", bidu.mensagem_tutor.lower())

    def test_mensagem_do_thor_cita_o_tutor(self):
        texto = self.ia.analisar_pet(3).mensagem_tutor
        self.assertIn("Ana", texto)
        self.assertIn("Thor", texto)

    def test_prompt_versionado_entra_na_geracao(self):
        prompt = self.ia.analisar_pet(3).prompt_tutor
        self.assertNotIn("{{contexto}}", prompt)
        self.assertIn("Thor", prompt)
        self.assertIn("Nunca invente", prompt)
        preenchido = preencher_prompt("sistema_veterinario.txt", {"pet": "Pipoca"})
        self.assertIn("Pipoca", preenchido)
        self.assertIn("decisão terapêutica", preenchido.lower())

    def test_retorno_depois_de_180_dias(self):
        pet = Pet(
            id_pet=1, id_tutor=1, nome="Rex", especie="Cachorro", cor="",
            idade=5, peso=15, rfid_uid="A1B2C3D4", status_internacao=None,
            gaiola=None, comportamento="",
        )
        recs = recomendar(
            pet=pet, vacinas=[], prontuarios=[],
            consultas=[{"id_pet": 1, "status": "Realizada", "data_consulta": "2025-01-01"}],
            medicamentos=[], internado=False, nivel_risco="baixo",
            clima_fora_faixa=False, identidade_divergente=False,
        )
        self.assertTrue(any("retorno" in rec.servico.lower() for rec in recs))

    def test_visao_do_tutor_omite_o_resumo_clinico(self):
        app = Aplicacao(suporte.ROOT / "data", suporte.ROOT / "web")
        jornada = app.jornada_tutor(5)
        self.assertIsNotNone(jornada)
        texto = jornada["pets"][0]["mensagem_tutor"]
        self.assertNotIn("resumo_clinico", jornada["pets"][0])
        self.assertIn("Bidu", texto)
        self.assertNotIn("Rex", texto)
        self.assertNotIn("RFID", texto)
        self.assertNotIn("cpf", jornada["tutor"])

    def test_relatorio_coloca_o_bidu_antes_do_thor(self):
        texto = texto_relatorio(self.ia)
        self.assertLess(texto.index("Bidu"), texto.index("Thor"))
        self.assertIn("27,0 °C", texto)
        self.assertIn("21,0 °C", texto)


if __name__ == "__main__":
    unittest.main()
