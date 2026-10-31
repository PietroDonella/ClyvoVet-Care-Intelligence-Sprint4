const $ = (id) => document.getElementById(id);

const NIVEL = { critico: "crítico", alto: "alto", medio: "médio", baixo: "baixo" };

const PRESETS = {
  "thor-calor": {
    gaiola: "G-04", temperatura: 32.4, umidade: 78,
    rfid_lido: "C3D4E5F6", pet_esperado_id: 3, topico: "clyvovet/internacao/temp",
  },
  "thor-conforto": {
    gaiola: "G-04", temperatura: 22, umidade: 50,
    rfid_lido: "C3D4E5F6", pet_esperado_id: 3, topico: "clyvovet/internacao/temp",
  },
  "pipoca-frio": {
    gaiola: "G-07", temperatura: 17.1, umidade: 35,
    rfid_lido: "18293A4B", pet_esperado_id: 8, topico: "clyvovet/internacao/temp",
  },
  "bidu-troca": {
    gaiola: "G-02", temperatura: 24, umidade: 55,
    rfid_lido: "A1B2C3D4", pet_esperado_id: 7, topico: "clyvovet/triagem/rfid",
  },
  "bidu-ok": {
    gaiola: "G-02", temperatura: 24, umidade: 55,
    rfid_lido: "0718293A", pet_esperado_id: 7, topico: "clyvovet/triagem/rfid",
  },
};

const estado = {
  fila: [],
  selecionado: null,
  tutores: [],
  tutorId: null,
  enviando: false,
};

let marca = Date.parse("2026-10-30T15:00:00");

function proximaMarca() {
  marca += 1000;
  const data = new Date(marca);
  const p = (n) => String(n).padStart(2, "0");
  return `${data.getFullYear()}-${p(data.getMonth() + 1)}-${p(data.getDate())}T${p(data.getHours())}:${p(data.getMinutes())}:${p(data.getSeconds())}`;
}

async function api(caminho, opcoes) {
  const resposta = await fetch(caminho, opcoes);
  const texto = await resposta.text();
  const corpo = texto ? JSON.parse(texto) : null;
  if (!resposta.ok) {
    const mensagem = corpo && corpo.erros ? corpo.erros.join(" ") : "A API recusou a operação.";
    throw new Error(mensagem);
  }
  return corpo;
}

function el(tag, classe, texto) {
  const node = document.createElement(tag);
  if (classe) node.className = classe;
  if (texto != null) node.textContent = texto;
  return node;
}

function mostrar(aba) {
  $("vista-plantao").hidden = aba !== "plantao";
  $("vista-tutor").hidden = aba !== "tutor";
  $("vista-avaliacao").hidden = aba !== "avaliacao";
  for (const nome of ["plantao", "tutor", "avaliacao"]) {
    $("aba-" + nome).setAttribute("aria-pressed", nome === aba ? "true" : "false");
  }
  if (aba === "tutor") carregarTutor();
  if (aba === "avaliacao") carregarAvaliacao();
}

function renderFila() {
  const lista = $("fila");
  lista.replaceChildren();
  estado.fila.forEach((item, indice) => {
    const botao = el("button", "item risco-" + item.nivel_risco);
    botao.type = "button";
    botao.setAttribute("aria-pressed", item.id_pet === estado.selecionado ? "true" : "false");
    const pos = el("span", "pos", String(indice + 1));
    const quem = el("span");
    quem.append(el("strong", null, item.nome));
    const lugar = item.gaiola ? "gaiola " + item.gaiola : "ambulatorial";
    quem.append(el("small", null, `${item.especie} · ${item.idade} ano(s) · ${lugar}`));
    const pill = el("span", "pill", `${NIVEL[item.nivel_risco]} · ${item.score_risco}`);
    botao.append(pos, quem, pill);
    botao.addEventListener("click", () => {
      estado.selecionado = item.id_pet;
      renderFila();
      renderDetalhe();
    });
    lista.append(botao);
  });
}

function linhaAlerta(alerta) {
  const box = el("p", "alerta");
  box.append(el("strong", null, `[${alerta.nivel}] ${alerta.titulo}`));
  box.append(document.createTextNode(alerta.detalhe));
  return box;
}

function linhaServico(rec, modo) {
  const box = el("p", "servico");
  const titulo = modo === "tutor"
    ? rec.servico
    : `P${rec.prioridade} · ${rec.publico} · ${rec.servico}`;
  box.append(el("strong", null, titulo));
  box.append(document.createTextNode(rec.motivo));
  return box;
}

function renderDetalhe() {
  const painel = $("detalhe");
  const item = estado.fila.find((pet) => pet.id_pet === estado.selecionado);
  painel.replaceChildren();
  const titulo = el("h2", null, "Caso");
  titulo.id = "titulo-detalhe";
  painel.append(titulo);
  if (!item) {
    painel.append(el("p", "apoio", "Selecione um animal da fila."));
    return;
  }
  painel.append(el("h3", null, item.nome));
  const situacao = item.status_internacao || "Ambulatorial";
  const gaiola = item.gaiola ? `, gaiola ${item.gaiola}` : "";
  painel.append(el(
    "p",
    "meta",
    `${item.especie} · ${item.idade} ano(s) · ${item.peso} kg · tutor ${item.tutor_nome} · ${situacao}${gaiola}`
  ));
  painel.append(el("p", "meta", "Conforto deste perfil: " + item.faixa_conforto));
  const barra = el("div", "barra");
  const preenchido = el("span");
  preenchido.style.width = `${item.score_risco}%`;
  barra.append(preenchido);
  painel.append(barra);
  const pill = el("span", "pill risco-" + item.nivel_risco, `${NIVEL[item.nivel_risco]} · score ${item.score_risco}`);
  painel.append(pill);
  painel.append(el("p", null, item.acao_priorizada));

  const blocoLeitura = el("div", "bloco");
  blocoLeitura.append(el("h4", null, "Última leitura"));
  if (item.leitura) {
    const leitura = item.leitura;
    blocoLeitura.append(el(
      "p",
      null,
      `${leitura.timestamp} · ${leitura.gaiola} · ${leitura.temperatura} °C · ${leitura.umidade}% · RFID ${leitura.rfid_lido}`
    ));
  } else {
    blocoLeitura.append(el("p", null, "Sem leitura de internação. A priorização usa prontuário e vacinas."));
  }
  painel.append(blocoLeitura);

  const blocoAlertas = el("div", "bloco");
  blocoAlertas.append(el("h4", null, "Alertas"));
  if (item.alertas.length) item.alertas.forEach((alerta) => blocoAlertas.append(linhaAlerta(alerta)));
  else blocoAlertas.append(el("p", null, "Nenhum alerta de sensor ou de identidade."));
  painel.append(blocoAlertas);

  const blocoServicos = el("div", "bloco");
  blocoServicos.append(el("h4", null, "Serviços recomendados"));
  if (item.recomendacoes.length) item.recomendacoes.forEach((rec) => blocoServicos.append(linhaServico(rec)));
  else blocoServicos.append(el("p", null, "Nenhum serviço além da rotina."));
  painel.append(blocoServicos);

  const blocoResumo = el("div", "bloco");
  blocoResumo.append(el("h4", null, "Resumo para o veterinário"));
  blocoResumo.append(el("p", null, item.resumo_clinico));
  painel.append(blocoResumo);

  const blocoMsg = el("div", "bloco");
  blocoMsg.append(el("h4", null, "O que o tutor recebe"));
  blocoMsg.append(el("p", "mensagem", item.mensagem_tutor));
  painel.append(blocoMsg);
}

function preencherPets() {
  const select = $("campo-pet");
  const atual = select.value;
  select.replaceChildren();
  estado.fila.forEach((item) => {
    const opcao = el("option", null, `${item.id_pet} — ${item.nome}`);
    opcao.value = String(item.id_pet);
    select.append(opcao);
  });
  const valores = [...select.options].map((opcao) => opcao.value);
  if (valores.includes(atual)) select.value = atual;
  else if (valores.includes("3")) select.value = "3";
}

function preencherTutores() {
  const select = $("campo-tutor");
  select.replaceChildren();
  estado.tutores.forEach((tutor) => {
    const opcao = el("option", null, tutor.nome);
    opcao.value = String(tutor.id_tutor);
    select.append(opcao);
  });
  if (estado.tutorId) select.value = String(estado.tutorId);
}

async function carregarFila() {
  estado.fila = await api("/api/fila");
  if (!estado.fila.some((item) => item.id_pet === estado.selecionado)) {
    estado.selecionado = estado.fila.length ? estado.fila[0].id_pet : null;
  }
  if (!estado.tutorId && estado.fila.length) estado.tutorId = estado.fila[0].id_tutor;
  renderFila();
  renderDetalhe();
  preencherPets();
}

async function carregarTutor() {
  if (!estado.tutorId) return;
  let jornada;
  try {
    jornada = await api("/api/tutores/" + estado.tutorId);
  } catch (erro) {
    $("tutor-meta").textContent = erro.message;
    return;
  }
  $("tutor-meta").textContent = `${jornada.tutor.nome} · ${jornada.tutor.telefone}`;
  const caixa = $("cards-tutor");
  caixa.replaceChildren();
  jornada.pets.forEach((pet) => {
    const artigo = document.createElement("article");
    artigo.append(el("h3", null, pet.nome));
    artigo.append(el("p", "meta", `${pet.especie} · ${pet.idade} ano(s) · ${pet.peso} kg · prioridade ${NIVEL[pet.nivel_risco]}`));
    artigo.append(el("p", "mensagem", pet.mensagem_tutor));
    if (pet.recomendacoes.length) {
      const bloco = el("div", "bloco");
      bloco.append(el("h4", null, "Próximos passos"));
      pet.recomendacoes.forEach((rec) => bloco.append(linhaServico(rec, "tutor")));
      artigo.append(bloco);
    }
    caixa.append(artigo);
  });
}

async function carregarAvaliacao() {
  try {
    const relatorio = await api("/api/avaliacao");
    $("texto-avaliacao").textContent = relatorio.texto;
  } catch (erro) {
    $("texto-avaliacao").textContent = erro.message;
  }
}

async function publicar(parcial) {
  if (estado.enviando) return;
  estado.enviando = true;
  $("erro-leitura").textContent = "";
  const corpo = {
    timestamp: proximaMarca(),
    origem: "Painel CLYVO VET",
    topico: parcial.topico,
    gaiola: parcial.gaiola,
    temperatura: Number(parcial.temperatura),
    umidade: Number(parcial.umidade),
    rfid_lido: parcial.rfid_lido,
    pet_esperado_id: Number(parcial.pet_esperado_id),
  };
  try {
    await api("/api/leituras", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corpo),
    });
    estado.selecionado = corpo.pet_esperado_id;
    await carregarFila();
    const saude = await api("/api/saude");
    $("status-servico").textContent = `${saude.pets} pets na base · ${saude.leituras} leituras em memória · validação ${saude.validacao}`;
  } catch (erro) {
    $("erro-leitura").textContent = erro.message;
  } finally {
    estado.enviando = false;
  }
}

function lerFormulario() {
  return {
    gaiola: $("campo-gaiola").value.trim(),
    temperatura: $("campo-temp").value,
    umidade: $("campo-umidade").value,
    rfid_lido: $("campo-rfid").value.trim(),
    pet_esperado_id: $("campo-pet").value,
    topico: $("campo-topico").value,
  };
}

function aplicarPreset(preset) {
  $("campo-gaiola").value = preset.gaiola;
  $("campo-temp").value = preset.temperatura;
  $("campo-umidade").value = preset.umidade;
  $("campo-rfid").value = preset.rfid_lido;
  $("campo-pet").value = String(preset.pet_esperado_id);
  $("campo-topico").value = preset.topico;
  publicar(preset);
}

async function iniciar() {
  try {
    const [saude, tutores] = await Promise.all([api("/api/saude"), api("/api/tutores")]);
    estado.tutores = tutores;
    $("status-servico").textContent = `${saude.pets} pets na base · ${saude.leituras} leituras · validação ${saude.validacao}`;
    preencherTutores();
    await carregarFila();
    preencherTutores();
  } catch (erro) {
    $("status-servico").textContent = erro.message;
  }
}

$("aba-plantao").addEventListener("click", () => mostrar("plantao"));
$("aba-tutor").addEventListener("click", () => mostrar("tutor"));
$("aba-avaliacao").addEventListener("click", () => mostrar("avaliacao"));
$("campo-tutor").addEventListener("change", (evento) => {
  estado.tutorId = Number(evento.target.value);
  carregarTutor();
});
$("form-leitura").addEventListener("submit", (evento) => {
  evento.preventDefault();
  publicar(lerFormulario());
});
document.querySelectorAll("[data-preset]").forEach((botao) => {
  botao.addEventListener("click", () => aplicarPreset(PRESETS[botao.dataset.preset]));
});
$("restaurar").addEventListener("click", async () => {
  $("erro-leitura").textContent = "";
  await api("/api/reiniciar", { method: "POST" });
  estado.selecionado = null;
  await carregarFila();
  const saude = await api("/api/saude");
  $("status-servico").textContent = `${saude.pets} pets na base · ${saude.leituras} leituras · validação ${saude.validacao}`;
});

iniciar();
