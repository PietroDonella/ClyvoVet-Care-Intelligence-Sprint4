# Integração

A aplicação desta sprint é o ponto em que a interface, a base, a API e a IA se encontram. O plantão e o tutor não chamam o motor de regras. Eles chamam a API. A API chama o `CareIntelligence`.

## Rotas desta aplicação

| Método | Rota | Quem usa |
|---|---|---|
| GET | `/` | Tela |
| GET | `/api/saude` | Cabeçalho: pets, leituras, validação |
| GET | `/api/fila` | Fila do plantão, já ordenada |
| GET | `/api/pets/{id}` | Caso completo, inclusive alerta de coleira |
| GET | `/api/pets/{id}/prompts` | Prompt preenchido, para inspeção |
| GET | `/api/tutores` | Lista de tutores, sem CPF |
| GET | `/api/tutores/{id}` | Mensagem e próximos passos daquele tutor |
| GET | `/api/avaliacao` | O mesmo relatório do terminal |
| POST | `/api/leituras` | Payload no formato do MQTT |
| POST | `/api/reiniciar` | Volta às leituras do arquivo |

Uma leitura nova substitui a anterior daquele pet quando o timestamp é maior ou igual. O arquivo `leituras_iot.json` não é reescrito.

## API .NET já existente

Quando a API da CLYVO VET está no ar:

```text
python app.py --servidor --api http://127.0.0.1:5000
```

`cliente_api.py` lê:

- `GET /api/tutores`
- `GET /api/animais`
- `GET /api/consultas`
- `GET /api/prontuarios`

Nome, espécie, idade, peso, consulta e diagnóstico passam a vir desse JSON. RFID, gaiola, internação, vacina, medicação e comportamento continuam na base local, casados pelo id, porque essas colunas não estão na entidade `Pet` do .NET. O prontuário da API entra no pet pela consulta que aponta `idProntuario`.

O teste `tests/test_api_dotnet.py` faz essa mesclagem com um payload no formato da API, inclusive em PascalCase, e confere que a otite do Thor continua gerando reavaliação otológica.

Sem `--api`, a aplicação sobe com o JSON local. O cálculo, a tela e os testes usam essa base.

## Sensor

O corpo de `POST /api/leituras` é o JSON dos tópicos das sprints 1 e 2:

```json
{
  "timestamp": "2026-10-30T15:00:00",
  "origem": "ESP32 / Wokwi",
  "topico": "clyvovet/internacao/temp",
  "gaiola": "G-04",
  "temperatura": 32.4,
  "umidade": 78,
  "rfid_lido": "C3D4E5F6",
  "pet_esperado_id": 3
}
```

A tela publica esse corpo. Um broker MQTT real entraria pelo mesmo contrato.
