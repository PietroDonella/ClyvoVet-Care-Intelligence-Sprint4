# Dados que alimentam a IA

A base de demonstração está em `data/base_clinica.json` e `data/leituras_iot.json`. São os mesmos pets da API (Rex, Mia, Thor, Luna, Frajola, Nina, Bidu e Pipoca), com a extensão de coleira, gaiola, vacina, medicação e comportamento que a entidade `Pet` do .NET ainda não carrega.

O CPF fica no arquivo, alinhado ao cadastro, e não sai na API desta sprint nem na tela.

## O que cada grupo alimenta

| Grupo | Origem | Uso |
|---|---|---|
| Tutor | `TUTOR` / `GET /api/tutores` | Nome na mensagem. Telefone só na visão daquele tutor |
| Pet | `PET` / `GET /api/animais` | Espécie, idade e peso escolhem a faixa |
| Consulta | `CONSULTA` / `GET /api/consultas` | Status e data. Retorno quando a última realizada tem 180 dias ou mais |
| Prontuário | `PRONTUARIO` / `GET /api/prontuarios` | Diagnóstico. Na API .NET o prontuário não tem id do pet; o vínculo é `Consulta.idProntuario` |
| Vacina, medicação, RFID, gaiola, comportamento | Extensão local | Protocolo, tratamento ativo e alocação da internação |
| Sensor | MQTT `clyvovet/internacao/temp` e `clyvovet/triagem/rfid` | Temperatura, umidade, UID lido, gaiola e o pet que deveria estar nela |

## Validação

`validacao.py` roda antes de a IA aceitar a base e de novo em cada `POST /api/leituras`.

A base precisa de tutor existente, RFID único, status de consulta em `Agendada`, `Realizada` ou `Cancelada`, e status de vacina em `Em dia`, `Vencida` ou `Reforco pendente`.

A leitura precisa de tópico `clyvovet/...`, pet existente, temperatura entre 0 e 50 °C, umidade entre 0 e 100% e timestamp ISO. Uma temperatura 80 é recusada e o caso anterior permanece.

`python app.py --validar` confirma a carga. Os testes em `tests/test_regras.py` travam essa conferência.
