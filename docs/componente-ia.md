# Componente de IA implementado

A especificação ficou na 3ª sprint: priorizar a internação, recomendar serviço e explicar o próximo passo, com três técnicas no lugar em que o erro tem custo diferente. Esta sprint executa essa especificação.

## Motor de regras

Código: `src/ia_clyvovet/motor_regras.py`.

A faixa térmica depende de espécie e faixa etária. Filhote tem menos de 2 anos. Sênior tem 8 anos ou mais. Um desvio de 3 °C ou mais soma 45. Um desvio de 1 °C ou mais soma 25. Umidade fora da faixa soma 15. Filhote e sênior recebem mais 15 quando já existe desvio.

RFID trocado e RFID desconhecido são críticos. O score vai a no mínimo 90 e a ação é interromper o procedimento até validar o paciente. Essa saída não passa pelo gerador de texto.

Níveis: crítico se houver alerta crítico; alto a partir de 50; médio a partir de 25; baixo abaixo disso.

## Recomendação por conteúdo

Código: `src/ia_clyvovet/recomendador.py`.

O serviço sai do perfil e do histórico: vacina vencida, reforço pendente, otite, alergia, sobrepeso, medicação em uso, filhote, sênior e consulta realizada há 180 dias ou mais. A data de referência é 11/09/2026, a data da carga. O prazo de 180 dias é contado a partir dela, então o resultado não muda conforme o dia em que a aplicação é executada.

Cada item tem prioridade e público (`clinica` ou `tutor`). A base tem oito pets. Não há nota de serviço para treinar filtro colaborativo.

## Texto condicionado ao prompt

Código: `src/ia_clyvovet/ia_generativa.py` e arquivos em `prompts/`.

O contexto do pet, dos alertas e das recomendações entra no prompt versionado, no lugar de `{{contexto}}`. O texto exibido é montado a partir desse mesmo contexto, no próprio processo. A demo repete a mesma frase, não pede chave e não inventa dose. Em produção, o prompt preenchido é o corpo que segue para o LLM, sem mudar o orquestrador.

O tutor não recebe o nome do outro animal quando a coleira está trocada. O plantão recebe, no alerta, de quem é a tag.

## Orquestração

`CareIntelligence` em `orquestrador.py` lê a base, aplica a leitura mais recente de cada pet, chama as três peças e devolve um insight com score, ação, alertas, serviços, mensagem e resumo. A frase final do resumo é fixa: a decisão terapêutica permanece com o veterinário responsável.
