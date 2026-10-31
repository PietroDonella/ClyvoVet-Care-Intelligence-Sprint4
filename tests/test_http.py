import json
import threading
import time
import unittest
import urllib.error
import urllib.request

import suporte
from ia_clyvovet.servico_http import Aplicacao, iniciar_servidor


class TestHttp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.aplicacao = Aplicacao(suporte.ROOT / "data", suporte.ROOT / "web")
        cls.httpd = iniciar_servidor(cls.aplicacao, "127.0.0.1", 0)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"
        ultimo = None
        for _ in range(40):
            try:
                urllib.request.urlopen(cls.base + "/api/saude", timeout=1).close()
                return
            except urllib.error.URLError as exc:
                ultimo = exc
                time.sleep(0.05)
        raise RuntimeError(f"servidor não subiu: {ultimo}")

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def setUp(self):
        status, _ = self._post("/api/reiniciar", {})
        self.assertEqual(status, 200)

    def _get(self, caminho):
        try:
            with urllib.request.urlopen(self.base + caminho, timeout=3) as resposta:
                return resposta.status, resposta.read()
        except urllib.error.HTTPError as exc:
            corpo = exc.read()
            exc.close()
            return exc.code, corpo

    def _post(self, caminho, payload):
        requisicao = urllib.request.Request(
            self.base + caminho,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(requisicao, timeout=3) as resposta:
                return resposta.status, json.loads(resposta.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            corpo = json.loads(exc.read().decode("utf-8"))
            exc.close()
            return exc.code, corpo

    def test_interface_e_fila(self):
        status_html, html = self._get("/")
        self.assertEqual(status_html, 200)
        self.assertIn("CLYVO VET", html.decode("utf-8"))
        status, corpo = self._get("/api/fila")
        fila = json.loads(corpo.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(fila[0]["nome"], "Bidu")
        self.assertEqual(fila[0]["nivel_risco"], "critico")

    def test_post_invalido_e_leitura_que_alivia_o_thor(self):
        status, corpo = self._post(
            "/api/leituras",
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
        )
        self.assertEqual(status, 400)
        self.assertIn("erros", corpo)
        status, insight = self._post(
            "/api/leituras",
            {
                "timestamp": "2026-10-30T15:00:01",
                "origem": "teste",
                "topico": "clyvovet/internacao/temp",
                "gaiola": "G-04",
                "temperatura": 22,
                "umidade": 50,
                "rfid_lido": "C3D4E5F6",
                "pet_esperado_id": 3,
            },
        )
        self.assertEqual(status, 201)
        self.assertEqual(insight["nivel_risco"], "baixo")
        _, pet = self._get("/api/pets/3")
        self.assertEqual(json.loads(pet.decode("utf-8"))["score_risco"], 0)

    def test_tutor_e_avaliacao(self):
        status, corpo = self._get("/api/tutores/5")
        jornada = json.loads(corpo.decode("utf-8"))
        self.assertEqual(status, 200)
        self.assertEqual(jornada["tutor"]["nome"], "Eduardo Lima")
        self.assertNotIn("Rex", jornada["pets"][0]["mensagem_tutor"])
        status, relatorio = self._get("/api/avaliacao")
        texto = json.loads(relatorio.decode("utf-8"))["texto"]
        self.assertEqual(status, 200)
        self.assertIn("Pipoca", texto)


if __name__ == "__main__":
    unittest.main()
