# CLYVO VET — Care Intelligence (Sprint 4)

**Disruptive Architectures: IoT, IoB & Generative IA**

Grupo: Enzo Vaz (RM 561702) · Lucas Ryuji Fukuda (RM 562152) · Pietro Donella Salomão (RM 561722)

A 3ª sprint definiu o componente de IA. Esta sprint implementa esse componente dentro da aplicação: interface do plantão, visão do tutor, API, base clínica e leitura de sensor no mesmo fluxo.

A IA prioriza a internação, recomenda o serviço e redige a mensagem do tutor. A decisão terapêutica permanece com o veterinário responsável.

- Vídeo (YouTube, não listado): https://youtu.be/V-ly5bB0eyw
- IoT das sprints 1 e 2: [PietroDonella/IoT-Challenge](https://github.com/PietroDonella/IoT-Challenge)
- API .NET da CLYVO VET: [EnzoVazz/ClyvoVet](https://github.com/EnzoVazz/ClyvoVet)

## O que a aplicação faz

O plantão abre a fila e atende o primeiro nome. O tutor abre a mensagem daquele pet, com o próximo passo, sem ver a coleira de outro animal.

Três casos da base, já calculados:

| Pet | Leitura | Resultado |
|---|---|---|
| Bidu, gaiola G-02 | RFID lido é o do Rex, clima dentro da faixa | Risco crítico, score 90. Procedimento interrompido até conferir a identidade |
| Pipoca, gaiola G-07 | 17,1 °C, umidade 35%, gata filhote de 1,2 kg | Risco alto, score 75. Frio fora da faixa felina de filhote e reforço da V4 |
| Thor, gaiola G-04 | 32,4 °C, umidade 78%, cão sênior | Risco alto, score 75. Calor, vacina vencida, otite e medicação em uso |

A mesma temperatura não produz o mesmo score. A 27 °C, o cão sênior fica em 40 e o gato adulto fica em 0. A 21 °C, só o gato filhote sai da faixa.

## Tecnologias

| Camada | Tecnologia |
|---|---|
| Interface do plantão e do tutor | HTML, CSS e JavaScript, servidos pela própria aplicação |
| API desta sprint | Python 3.10+ (`http.server` da biblioteca padrão) |
| IA | Motor de regras, recomendação por conteúdo, texto condicionado aos prompts de `prompts/` |
| Base de demonstração | JSON em `data/`, no formato da API .NET / Oracle |
| Integração com a API .NET | `python app.py --servidor --api http://host:porta` lê `/api/tutores`, `/api/animais`, `/api/consultas` e `/api/prontuarios` |
| IoT já entregue | ESP32, MFRC522, DHT22, MQTT, HiveMQ, tópicos `clyvovet/internacao/temp` e `clyvovet/triagem/rfid` |

Não há dependência externa. Só Python 3.10 ou superior.

## Como executar

Na pasta do projeto:

```text
python app.py --servidor
```

Abra http://127.0.0.1:8080

Outros comandos:

```text
python app.py --relatorio
python app.py --validar
python -m unittest discover -s tests -v
python app.py
python app.py --pet 7
python app.py --json
python app.py --servidor --api http://127.0.0.1:5000
```

`--api` usa a API .NET quando ela está no ar. Sem essa flag, a aplicação sobe com `data/base_clinica.json` e as três leituras de `data/leituras_iot.json`.

Na tela, os botões de caso publicam uma leitura nova. **Restaurar base** volta aos três payloads originais. A leitura publicada fica em memória: reiniciar o processo também volta ao arquivo.

Para acompanhar a demonstração:

1. A fila abre no Bidu.
2. O caso do Bidu mostra que a tag é do Rex. A aba Tutor, no Eduardo Lima, fala de segurança e não cita o Rex.
3. **Thor na faixa** (22 °C e 50%) derruba o score climático para 0 e mantém a vacina vencida.
4. A aba Avaliação imprime o mesmo texto de `python app.py --relatorio`.

## Estrutura do repositório

```
├── README.md
├── app.py                     ← aplicação executável
├── data/
│   ├── base_clinica.json      ← tutores, pets, prontuários, vacinas, medicação
│   └── leituras_iot.json      ← payload MQTT (temp + RFID)
├── src/ia_clyvovet/
│   ├── motor_regras.py
│   ├── recomendador.py
│   ├── ia_generativa.py
│   ├── orquestrador.py
│   ├── validacao.py
│   ├── cliente_api.py
│   ├── avaliacao.py
│   └── servico_http.py
├── prompts/                   ← prompts de produção para o LLM
├── web/                       ← interface do plantão e do tutor
├── tests/                     ← cenários da jornada, da API e da tela
└── docs/
```

## Onde está cada parte da entrega

| Parte | Onde |
|---|---|
| IA implementada a partir da sprint anterior | `src/ia_clyvovet/` |
| Interface, API, base e IA no mesmo fluxo | `web/` e `src/ia_clyvovet/servico_http.py` |
| Dados preparados e validados | `data/` e `src/ia_clyvovet/validacao.py` |
| Testes dos cenários de uso | `tests/` |
| Avaliação da personalização | `python app.py --relatorio` e a aba Avaliação |
| Documentação técnica | `docs/` |

## Resultados

Com a carga atual, a ordem do plantão é Bidu (crítico, 90), Pipoca (alto, 75), Thor (alto, 75) e, depois, Frajola, Luna, Mia, Nina e Rex em risco baixo. O quadro completo, com a personalização a 27 °C e a 21 °C, está em `docs/testes-e-resultados.md`. Os 22 testes automatizados cobrem essa fila, a troca de RFID, a leitura que alivia o Thor, a visão do tutor e a mesclagem com o JSON da API .NET.
