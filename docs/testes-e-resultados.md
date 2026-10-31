# Testes e resultados

Os testes estão em `tests/`. Comando:

```text
python -m unittest discover -s tests -v
```

São 22 testes. Eles travam a fila da base, os scores de personalização, o RFID crítico, a recusa de temperatura absurda, a mensagem do tutor, o prompt preenchido, a visão sem CPF e sem o nome do outro animal, a mesclagem com o JSON da API .NET e o HTTP da interface.

## Personalização

A função `quadro_personalizacao` aplica a mesma leitura a quatro perfis. Os testes exigem estes scores:

| Leitura | Cão adulto | Cão sênior | Gato adulto | Gato filhote de 1,2 kg |
|---|---|---|---|---|
| 27 °C e 55% | 25, médio | 40, médio | 0, baixo | 0, baixo |
| 21 °C e 55% | 0, baixo | 0, baixo | 0, baixo | 40, médio |

O gato filhote só sai da faixa no frio. O cão sênior sai antes do cão adulto no calor. Essa é a personalização do acompanhamento: a sala é a mesma, o limiar é do animal.

## Casos da base

| Pet | Score | Nível | Por quê |
|---|---|---|---|
| Bidu | 90 | crítico | Gaiola G-02 deveria ler `0718293A`. A tag lida é `A1B2C3D4`, do Rex. O clima, 24 °C e 55%, está na faixa de cão adulto |
| Pipoca | 75 | alto | 17,1 °C está 4,9 °C abaixo da faixa de gato filhote (22–28 °C), umidade 35% abaixo de 40%, e o peso de 1,2 kg aumenta o desvio |
| Thor | 75 | alto | 32,4 °C está acima da faixa de cão sênior (20–25 °C), umidade 78% acima de 65%, com peso extra de sênior |

Uma leitura posterior do Thor a 22 °C, 50% e com o RFID `C3D4E5F6` zera o score climático. A vacina vencida continua na lista. O risco do sensor e o cuidado contínuo andam separados, de propósito.

## Relatório gerado pelo código

Saída de `python app.py --relatorio` com a base desta pasta:

```text
CLYVO VET — avaliação da Care Intelligence (4ª sprint)

Base validada: 6 tutores, 8 pets, 3 leituras IoT.
Data de referência das recomendações: 2026-09-11.

Mesma sala, perfis diferentes.
Leitura 27,0 °C e 55% de umidade:
  Cachorro adulto        score  25  medio     Cachorro adulto: 18–26 °C, umidade 40–70%
  Cachorro senior        score  40  medio     Cachorro senior: 20–25 °C, umidade 40–65%
  Gato adulto            score   0  baixo     Gato adulto: 20–27 °C, umidade 40–70%
  Gato filhote           score   0  baixo     Gato filhote: 22–28 °C, umidade 40–65%
Leitura 21,0 °C e 55% de umidade:
  Cachorro adulto        score   0  baixo     Cachorro adulto: 18–26 °C, umidade 40–70%
  Cachorro senior        score   0  baixo     Cachorro senior: 20–25 °C, umidade 40–65%
  Gato adulto            score   0  baixo     Gato adulto: 20–27 °C, umidade 40–70%
  Gato filhote           score  40  medio     Gato filhote: 22–28 °C, umidade 40–65%

Fila do plantão com as leituras da base:

  1. Bidu       critico   90  G-02          Conferir identidade RFID e interromper procedimento até validar o paciente.
  2. Pipoca     alto      75  G-07          Priorizar este animal na ronda de internação e ajustar temperatura/umidade da gaiola.
  3. Thor       alto      75  G-04          Priorizar este animal na ronda de internação e ajustar temperatura/umidade da gaiola.
  4. Frajola    baixo      0  ambulatorial  Pedir à equipe: Vacinação / atualização de protocolo.
  5. Luna       baixo      0  ambulatorial  Oferecer ao tutor: Retorno para reforço vacinal.
  6. Mia        baixo      0  ambulatorial  Oferecer ao tutor: Acompanhamento dermatológico.
  7. Nina       baixo      0  ambulatorial  Pedir à equipe: Vacinação / atualização de protocolo.
  8. Rex        baixo      0  ambulatorial  Manter acompanhamento de rotina.

A conduta clínica permanece com o veterinário responsável.
```

A aba Avaliação da interface mostra este mesmo texto, vindo de `GET /api/avaliacao`.
