// ==============================
//          VARIÁVEIS GLOBAIS
// ==============================
let isRequestInProgress = false;
let loteriaAtual = "megasena";
let carregandoResultados = false;
let artigosVisiveis = 5;

// Gráficos Chart.js
let graficos = {
    maisSorteados: null,
    menosSorteados: null,
    primos: null,
    paresImpares: null,
    maisSorteadosRecentes: null,
    menosSorteadosRecentes: null
};

// ==============================
//       CONFIGURAÇÕES
// ==============================
const lotteryConfig = {
    megasena:   { nome: "Mega-Sena",   min_dezenas: 6,  max_dezenas: 20, num_bolas: 6,  universo: 60,  default_dezenas: 6 },
    quina:      { nome: "Quina",       min_dezenas: 5,  max_dezenas: 15, num_bolas: 5,  universo: 80,  default_dezenas: 5 },
    lotofacil:  { nome: "Lotofácil",   min_dezenas: 15, max_dezenas: 20, num_bolas: 15, universo: 25,  default_dezenas: 15 },
    diadesorte: { nome: "Dia de Sorte",min_dezenas: 7,  max_dezenas: 15, num_bolas: 7,  universo: 31,  default_dezenas: 7 },
    duplasena:  { nome: "Dupla Sena",  min_dezenas: 6,  max_dezenas: 15, num_bolas: 6,  universo: 50,  default_dezenas: 6 },
    lotomania:  { nome: "Lotomania",   min_dezenas: 50, max_dezenas: 50, num_bolas: 20, universo: 100, default_dezenas: 50 }
};

const totalArtigos = 10;
const cooldownTimes = { montecarlo: 10 };
const meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];

// ==============================
//        UTILITÁRIOS
// ==============================
function getElement(id) {
    return document.getElementById(id);
}

function getElements(selector) {
    return document.querySelectorAll(selector);
}

// ==============================
//        COPIAR NÚMEROS
// ==============================
function copiarNumeros(element) {
    const jogo = element.closest(".jogo");
    let texto = "";
    
    if (jogo) {
        texto = [...jogo.querySelectorAll(".numero")].map(el => el.textContent).join(" ");
    } else {
        texto = element.getAttribute("data-copy-text");
    }
    
    if (!texto) return;
    
    navigator.clipboard.writeText(texto).then(() => {
        mostrarFeedbackCopia(element);
    }).catch(error => {
        console.error("Falha ao copiar:", error);
        alert("Falha ao copiar. Por favor, copie manualmente: " + texto);
    });
}

function mostrarFeedbackCopia(element) {
    const originalHtml = element.innerHTML;
    const originalStyle = element.style.background;
    
    element.innerHTML = '<i class="fa-solid fa-check"></i>';
    if (!element.closest(".jogo")) {
        element.innerHTML += ' Copiado!';
        element.style.background = "var(--cor-sucesso)";
    }
    
    setTimeout(() => {
        element.innerHTML = originalHtml;
        if (originalStyle) element.style.background = originalStyle;
        else element.style.removeProperty("background");
    }, 2000);
}

// ==============================
//      GERENCIAR ESTADO
// ==============================
function setGeradorEstado(loading) {
    isRequestInProgress = loading;
    
    const botaoGerar = getElement("botao-gerar-principal");
    if (botaoGerar) botaoGerar.disabled = loading;
    
    getElements(".seletor-custom, #numeros-ancora").forEach(element => {
        element.disabled = loading;
    });
}

// ==============================
//      CONTROLE DE LOTERIA
// ==============================
function mudarLoteria(loteria) {
    loteriaAtual = loteria;
    const config = lotteryConfig[loteriaAtual];
    
    // Atualizar display da loteria
    const loteriaElement = getElement("loteria-selecionada");
    if (loteriaElement) {
        loteriaElement.textContent = config.nome;
        loteriaElement.style.opacity = 1;
    }
    
    // Sincronizar selects
    const selectResultados = getElement("loteria-select-resultados");
    if (selectResultados) selectResultados.value = loteria;
    
    const nomeResultados = getElement("nome-loteria-resultados");
    if (nomeResultados) nomeResultados.textContent = config.nome;
    
    // Atualizar opções
    atualizarOpcoesDezenas();
    atualizarOpcoesQuantidade();
    handleEstrategiaChange();
    
    // Limpar conteúdo anterior
    limparResultadosAnteriores();
    
    // Carregar novos resultados
    carregarUltimosResultados(loteria);
}

function mudarLoteriaResultados(loteria) {
    const config = lotteryConfig[loteria];
    const nomeElement = getElement("nome-loteria-resultados");
    
    if (nomeElement) nomeElement.textContent = config.nome;
    carregarUltimosResultados(loteria);
}

function limparResultadosAnteriores() {
    const areaResultados = getElement("area-resultados");
    if (areaResultados) areaResultados.innerHTML = "";
    
    const areaEstatisticas = getElement("area-estatisticas");
    if (areaEstatisticas) areaEstatisticas.style.display = "none";
    
    const botaoEstatisticas = document.querySelector("#estatisticas .botao-gerar");
    if (botaoEstatisticas) {
        botaoEstatisticas.style.display = "block";
        botaoEstatisticas.disabled = false;
        botaoEstatisticas.innerHTML = "Estatísticas";
    }
}

// ==============================
//      ATUALIZAR OPÇÕES
// ==============================
function atualizarOpcoesDezenas() {
    const dezenasSelect = getElement("dezenas-select");
    if (!dezenasSelect) return;
    
    const config = lotteryConfig[loteriaAtual];
    dezenasSelect.innerHTML = "";
    
    for (let i = config.min_dezenas; i <= config.max_dezenas; i++) {
        const option = document.createElement("option");
        option.value = i;
        option.textContent = `${i} Dezenas`;
        dezenasSelect.appendChild(option);
    }
}

function atualizarOpcoesQuantidade() {
    const quantidadeSelect = getElement("quantidade-select");
    if (!quantidadeSelect) return;
    
    quantidadeSelect.innerHTML = "";
    
    for (let i = 1; i <= 10; i++) {
        const option = document.createElement("option");
        option.value = i;
        option.textContent = `${String(i).padStart(2, "0")} ${i > 1 ? "Jogos" : "Jogo"}`;
        quantidadeSelect.appendChild(option);
    }
}

// ==============================
//      CONTROLE DE ESTRATÉGIA
// ==============================
function handleEstrategiaChange() {
    const elementos = {
        estrategia: getElement("estrategia-select"),
        dezenas: getElement("dezenas-select"),
        quantidade: getElement("quantidade-select"),
        ancora: getElement("numeros-ancora")
    };
    
    if (!elementos.estrategia) return;
    
    const estrategia = elementos.estrategia.value;
    const config = lotteryConfig[loteriaAtual];
    const isEspecial = estrategia === "montecarlo";
    
    if (isEspecial) {
        elementos.dezenas.value = config.num_bolas;
        elementos.quantidade.value = 1;
        elementos.ancora.value = "";
    }
    
    Object.values(elementos).slice(1).forEach(el => {
        el.disabled = isEspecial;
    });
}

// ==============================
//      GERAÇÃO DE PALPITES
// ==============================
async function gerarPalpites() {
    if (isRequestInProgress) return;
    
    const elementos = {
        resultados: getElement("area-resultados"),
        estrategia: getElement("estrategia-select"),
        dezenas: getElement("dezenas-select"),
        quantidade: getElement("quantidade-select"),
        ancora: getElement("numeros-ancora")
    };
    
    if (!elementos.resultados || !elementos.estrategia) return;
    
    const parametros = {
        estrategia: elementos.estrategia.value,
        dezenas: elementos.dezenas.value,
        quantidade: elementos.quantidade.value,
        ancora: elementos.ancora.value
    };
    
    setGeradorEstado(true);
    elementos.resultados.innerHTML = '<div class="spinner"></div>';
    
    try {
        const url = construirURL(parametros);
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`Erro na comunicação: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(`Erro no servidor: ${data.error}`);
        }
        
        const jogos = (parametros.estrategia === "montecarlo") 
            ? [data.jogo] : data;
        
        renderizarJogos(jogos, elementos.resultados);
        
    } catch (error) {
        console.error("Erro ao gerar palpites:", error);
        elementos.resultados.innerHTML = `<p style="color: #ff8a80;">Falha na conexão. Tente novamente em alguns segundos.</p>`;
    } finally {
        aplicarCooldown(parametros.estrategia);
    }
}

function construirURL(parametros) {
    const { estrategia, quantidade, dezenas, ancora } = parametros;
    
    if (estrategia === "montecarlo") {
        return `/get-monte-carlo-game?loteria=${loteriaAtual}&ancora=${ancora}`;
    }
    
    return `/get-games/${quantidade}?loteria=${loteriaAtual}&estrategia=${estrategia}&dezenas=${dezenas}&ancora=${ancora}`;
}

function aplicarCooldown(estrategia) {
    const cooldownTime = cooldownTimes[estrategia];
    
    if (!cooldownTime) {
        setGeradorEstado(false);
        handleEstrategiaChange();
        return;
    }
    
    const botaoGerar = getElement("botao-gerar-principal");
    if (!botaoGerar) return;
    
    let contador = cooldownTime;
    botaoGerar.innerHTML = `Aguarde ${contador}s...`;
    
    const intervalId = setInterval(() => {
        contador--;
        if (contador > 0) {
            botaoGerar.innerHTML = `Aguarde ${contador}s...`;
        } else {
            clearInterval(intervalId);
            botaoGerar.innerHTML = "Gerar Palpites";
            setGeradorEstado(false);
            handleEstrategiaChange();
        }
    }, 1000);
}

// ==============================
//      RENDERIZAÇÃO DE JOGOS
// ==============================
function renderizarJogos(jogos, container) {
    if (!container) return;

    container.innerHTML = "<h2>Boa sorte!</h2>";

    jogos.forEach(jogo => {
        const jogoDiv = criarElementoJogo(jogo);
        container.appendChild(jogoDiv);
    });

    adicionarInstrucaoAposta(container);
}

function criarElementoJogo(jogo) {
    const jogoDiv = document.createElement("div");
    jogoDiv.className = "jogo";

    const numerosContainer = document.createElement("div");
    numerosContainer.className = "numeros-container";

    const numerosDoJogo = jogo.trim().split(/\s+/);

    // Lógica específica para Dupla Sena na área de geração de palpites
    if (loteriaAtual === "duplasena" && numerosDoJogo.length === 12) {
        // CORREÇÃO: Manter ordem original para Dupla Sena
        const primeiroSorteio = numerosDoJogo.slice(0, 6); // SEM .sort()
        const segundoSorteio = numerosDoJogo.slice(6, 12); // SEM .sort()

        const divPrimeiroSorteio = document.createElement("div");
        divPrimeiroSorteio.className = "sorteio-header";
        divPrimeiroSorteio.textContent = "1º Sorteio:";
        numerosContainer.appendChild(divPrimeiroSorteio);
        
        primeiroSorteio.forEach(numero => {
            const numeroSpan = document.createElement("span");
            numeroSpan.className = "numero";
            numeroSpan.textContent = numero;
            numerosContainer.appendChild(numeroSpan);
        });

        const divSegundoSorteio = document.createElement("div");
        divSegundoSorteio.className = "sorteio-header";
        divSegundoSorteio.textContent = "2º Sorteio:";
        numerosContainer.appendChild(divSegundoSorteio);
        
        segundoSorteio.forEach(numero => {
            const numeroSpan = document.createElement("span");
            numeroSpan.className = "numero";
            numeroSpan.textContent = numero;
            numerosContainer.appendChild(numeroSpan);
        });

    } else {
        // Para outras loterias, ordenar normalmente (opcional)
        const numerosOrdenados = [...numerosDoJogo].sort((a, b) => a - b);
        numerosOrdenados.forEach(numero => {
            const numeroSpan = document.createElement("span");
            numeroSpan.className = "numero";
            numeroSpan.textContent = numero;
            numerosContainer.appendChild(numeroSpan);
        });
    }

    // Dia de Sorte: adicionar mês
    if (loteriaAtual === "diadesorte") {
        numerosContainer.appendChild(criarMesSorte());
    }

    // Botão copiar
    jogoDiv.appendChild(numerosContainer);
    jogoDiv.appendChild(criarBotaoCopiar());

    return jogoDiv;
}

// Funções auxiliares
function criarNumeroSpan(numero) {
    const span = document.createElement("span");
    span.className = "numero";
    span.textContent = numero;
    return span;
}

function criarHeaderSorteio(texto) {
    const div = document.createElement("div");
    div.className = "sorteio-header";
    div.textContent = texto;
    return div;
}

function criarMesSorte() {
    const mesAleatorio = meses[Math.floor(Math.random() * meses.length)];
    const mesSpan = document.createElement("span");
    mesSpan.textContent = `| Mês: ${mesAleatorio}`;
    mesSpan.style.cssText = "font-weight:bold; margin-left:15px; font-size: 1.2rem;";
    return mesSpan;
}

function criarBotaoCopiar() {
    const botao = document.createElement("button");
    botao.className = "botao-copiar";
    botao.innerHTML = '<i class="fa-regular fa-copy"></i>';
    botao.title = "Copiar números";
    botao.onclick = () => copiarNumeros(botao);
    return botao;
}

function adicionarInstrucaoAposta(container) {
    const instrucao = document.createElement("p");
    instrucao.className = "instrucao-aposta";
    instrucao.textContent = "Caso queira concorrer com os números gerados no site, você precisa registrá-los em uma aposta oficial, em qualquer agência lotérica ou no site de apostas da Caixa Econômica Federal®, por sua conta e riscos. Boa sorte!";
    container.appendChild(instrucao);
}

// ==============================
//        ESTATÍSTICAS
// ==============================
async function carregarChart() {
    if (!window.Chart) {
        await import('https://cdn.jsdelivr.net/npm/chart.js');
    }
}

async function exibirEstatisticas() {
    const botaoEstatisticas = document.querySelector("#estatisticas .botao-gerar");
    
    if (isRequestInProgress || !botaoEstatisticas || botaoEstatisticas.disabled) return;
    
    await carregarChart();
    
    isRequestInProgress = true;
    botaoEstatisticas.disabled = true;
    botaoEstatisticas.innerHTML = '<div class="spinner" style="width: 25px; height: 25px; margin: 0 auto;"></div> Carregando...';
    
    try {
        const dados = await buscarDadosEstatisticas();
        atualizarInfoEstatisticas(dados.gerais);
        criarTodosGraficos(dados);
        
        const areaEstatisticas = getElement("area-estatisticas");
        if (areaEstatisticas) areaEstatisticas.style.display = "block";
        
        botaoEstatisticas.style.display = "none";
        
    } catch (error) {
        console.error("Erro ao carregar estatísticas:", error);
        mostrarErroEstatisticas(error.message);
        botaoEstatisticas.innerHTML = "Estatísticas";
        botaoEstatisticas.disabled = false;
    } finally {
        isRequestInProgress = false;
    }
}

async function buscarDadosEstatisticas() {
    try {
        const [responseGeral, responseRecente] = await Promise.all([
            fetch(`/get-stats?loteria=${loteriaAtual}`),
            fetch(`/get-stats-recentes?loteria=${loteriaAtual}`)
        ]);
        
        if (!responseGeral.ok) {
            throw new Error(`Erro ${responseGeral.status}: ${responseGeral.statusText}`);
        }
        if (!responseRecente.ok) {
            throw new Error(`Erro ${responseRecente.status}: ${responseRecente.statusText}`);
        }
        
        const dadosGerais = await responseGeral.json();
        const dadosRecentes = await responseRecente.json();
        
        if (dadosGerais.error) {
            throw new Error(`Backend: ${dadosGerais.error}`);
        }
        if (dadosRecentes.error) {
            throw new Error(`Backend: ${dadosRecentes.error}`);
        }
        
        // Verificar se os dados necessários existem
        if (!dadosGerais.frequencia || !Array.isArray(dadosGerais.frequencia)) {
            throw new Error("Dados de frequência inválidos recebidos do servidor.");
        }
        if (!dadosRecentes.frequencia_recente || !Array.isArray(dadosRecentes.frequencia_recente)) {
            throw new Error("Dados de frequência recente inválidos recebidos do servidor.");
        }
        
        return { gerais: dadosGerais, recentes: dadosRecentes };
        
    } catch (error) {
        console.error("Erro detalhado ao buscar estatísticas:", error);
        throw new Error(`Falha na comunicação com o servidor: ${error.message}`);
    }
}

function atualizarInfoEstatisticas(dados) {
    const nomeLoteria = lotteryConfig[loteriaAtual].nome;
    const ultimoConcursoInfo = getElement("ultimo-concurso-info");
    if (ultimoConcursoInfo) {
        ultimoConcursoInfo.innerHTML = `Análise da ${nomeLoteria}: até o concurso ${dados.ultimo_concurso}`;
    }
}

function criarTodosGraficos(dados) {
    // Destruir gráficos existentes
    Object.values(graficos).forEach(grafico => {
        if (grafico) grafico.destroy();
    });
    
    const opcoesPadrao = {
        scales: {
            y: { ticks: { color: "#FFFDE7" }, grid: { color: "rgba(255, 255, 255, 0.2)" } },
            x: { ticks: { color: "#FFFDE7" }, grid: { color: "transparent" } }
        },
        plugins: { legend: { labels: { color: "#FFFDE7" }, onClick: null } }
    };
    
    graficos.maisSorteados = criarGrafico("grafico-mais-sorteados", dados.gerais.frequencia, "desc", "Vezes Sorteado", "#FFD700", opcoesPadrao);
    graficos.menosSorteados = criarGrafico("grafico-menos-sorteados", dados.gerais.frequencia, "asc", "Vezes Sorteado", "#90CAF9", opcoesPadrao);
    graficos.maisSorteadosRecentes = criarGrafico("grafico-mais-sorteados-recentes", dados.recentes.frequencia_recente, "desc", "Vezes Sorteado (Últimos 100)", "#FFECB3", opcoesPadrao);
    graficos.menosSorteadosRecentes = criarGrafico("grafico-menos-sorteados-recentes", dados.recentes.frequencia_recente, "asc", "Vezes Sorteado (Últimos 100)", "#BBDEFB", opcoesPadrao);
    
    graficos.primos = criarGraficoPrimos(dados.gerais.stats_primos, opcoesPadrao);
    graficos.paresImpares = criarGraficoParesImpares(dados.gerais.stats_pares, opcoesPadrao);
}

function criarGrafico(canvasId, dados, ordem, label, cor, opcoes) {
    const canvas = getElement(canvasId);
    if (!canvas) return null;
    
    const dadosOrdenados = [...dados]
        .sort((a, b) => ordem === "desc" ? b.frequencia - a.frequencia : a.frequencia - b.frequencia)
        .slice(0, 10);
    
    return new Chart(canvas.getContext("2d"), {
        type: "bar",
        data: {
            labels: dadosOrdenados.map(item => `Nº ${item.numero}`),
            datasets: [{
                label: label,
                data: dadosOrdenados.map(item => item.frequencia),
                backgroundColor: cor
            }]
        },
        options: opcoes
    });
}

function criarGraficoPrimos(dadosPrimos, opcoes) {
    const canvas = getElement("grafico-primos");
    if (!canvas) return null;
    
    const labels = Object.keys(dadosPrimos)
        .sort((a, b) => parseInt(a) - parseInt(b))
        .map(key => `${key} Primos`);
    
    const dados = Object.keys(dadosPrimos)
        .sort((a, b) => parseInt(a) - parseInt(b))
        .map(key => dadosPrimos[key]);
    
    return new Chart(canvas.getContext("2d"), {
        type: "bar",
        data: {
            labels: labels,
            datasets: [{
                label: "Sorteios",
                data: dados,
                backgroundColor: "#81C784"
            }]
        },
        options: opcoes
    });
}

function criarGraficoParesImpares(dadosPares, opcoes) {
    const canvas = getElement("grafico-pares-impares");
    if (!canvas) return null;
    
    const numBolas = lotteryConfig[loteriaAtual].num_bolas;
    const labels = Object.keys(dadosPares)
        .sort((a, b) => parseInt(a) - parseInt(b))
        .map(key => `${key} Pares / ${numBolas - parseInt(key)} Ímpares`);
    
    const dados = Object.keys(dadosPares)
        .sort((a, b) => parseInt(a) - parseInt(b))
        .map(key => dadosPares[key]);
    
    return new Chart(canvas.getContext("2d"), {
        type: "bar",
        data: {
            labels: labels,
            datasets: [{
                label: "Sorteios",
                data: dados,
                backgroundColor: "#FF8A65"
            }]
        },
        options: opcoes
    });
}

function mostrarErroEstatisticas(mensagem) {
    const areaEstatisticas = getElement("area-estatisticas");
    if (areaEstatisticas) {
        areaEstatisticas.innerHTML = `<p style="color: #ff8a80;">${mensagem}</p>`;
        areaEstatisticas.style.display = "block";
    }
}

// ==============================
//        ÚLTIMOS RESULTADOS
// ==============================
async function carregarUltimosResultados(loteria) {
    if (carregandoResultados) return;
    
    carregandoResultados = true;
    const listaResultados = getElement("lista-ultimos-resultados");
    if (!listaResultados) {
        carregandoResultados = false;
        return;
    }
    
    listaResultados.innerHTML = '<div class="spinner"></div>';
    
    try {
        const response = await fetch(`/get-ultimos-resultados?loteria=${loteria}`);
        
        if (!response.ok) {
            throw new Error("Falha ao carregar os resultados.");
        }
        
        const resultados = await response.json();
        
        if (resultados.error) {
            throw new Error(resultados.error);
        }
        
        if (resultados.length === 0) {
            listaResultados.innerHTML = "<p>Nenhum resultado encontrado para esta loteria.</p>";
            return;
        }
        
        listaResultados.innerHTML = resultados.map(resultado => criarHtmlResultado(resultado, loteria)).join("");
        
    } catch (error) {
        console.error("Erro ao carregar últimos resultados:", error);
        listaResultados.innerHTML = `<p style="color: #ff8a80;">Não foi possível carregar os resultados. Tente novamente mais tarde.</p>`;
    } finally {
        carregandoResultados = false;
    }
}

function criarHtmlResultado(resultado, loteria) {
    const statusHtml = criarStatusHtml(resultado);
    const mesHtml = criarMesHtml(resultado, loteria);
    const dataFormatada = formatarData(resultado.data);
    let dezenasHtml = `<div class="resultado-dezenas">${resultado.dezenas}</div>`;

    // Lógica específica para Dupla Sena exibir os dois sorteios
    if (loteria === "duplasena" && resultado.dezenas) {
        const dezenasArray = resultado.dezenas.split(' ');
        
        // CORREÇÃO: Verificar se temos 12 dezenas (2 sorteios) e MANTER A ORDEM ORIGINAL
        if (dezenasArray.length === 12) {
            const primeiroSorteio = dezenasArray.slice(0, 6); // MANTER ORDEM ORIGINAL
            const segundoSorteio = dezenasArray.slice(6, 12); // MANTER ORDEM ORIGINAL

            dezenasHtml = `
                <div class="duplasena-sorteios">
                    <div class="sorteio-header">1º Sorteio:</div>
                    <div class="resultado-dezenas">${primeiroSorteio.join(' ')}</div>
                    <div class="sorteio-header">2º Sorteio:</div>
                    <div class="resultado-dezenas">${segundoSorteio.join(' ')}</div>
                </div>
            `;
        } else {
            // Fallback: mostrar como dezenas únicas se não tiver 12 números
            dezenasHtml = `<div class="resultado-dezenas">${resultado.dezenas}</div>`;
        }
    }
    
    return `
        <div class="resultado-item">
            <div class="resultado-header">
                <span class="resultado-concurso">Concurso ${resultado.concurso}</span>
                <span class="resultado-data">${dataFormatada}</span>
            </div>
            ${dezenasHtml}
            ${mesHtml}
            <div class="resultado-status">${statusHtml}</div>
        </div>
    `;
}

function criarStatusHtml(resultado) {
    if (resultado.acumulou) {
        let html = `<span class="status-acumulou">ACUMULOU</span>`;
        if (resultado.valor_acumulado) {
            html += `<div class="valor-acumulado">Prêmio estimado: R$ ${resultado.valor_acumulado.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</div>`;
        }
        return html;
    }
    
    const labelGanhador = resultado.ganhadores > 1 ? "Ganhadores" : "Ganhador";
    return `<span class="status-ganhador">${resultado.ganhadores} ${labelGanhador}</span>`;
}

function criarMesHtml(resultado, loteria) {
    if (loteria === "diadesorte" && resultado.mes_sorte) {
        return `<div class="resultado-mes">Mês da Sorte: <strong>${resultado.mes_sorte}</strong></div>`;
    }
    return "";
}

function formatarData(data) {
    if (!data || !data.includes("/")) return data || "";
    
    const partes = data.split("/");
    if (partes.length !== 3) return data;
    
    const [parte1, parte2, parte3] = partes.map(p => parseInt(p));
    
    // Se primeira parte > 12, assumir DD/MM/YYYY
    if (parte1 > 12) return data;
    
    // Se segunda parte > 12, converter MM/DD/YYYY -> DD/MM/YYYY
    if (parte2 > 12) return `${partes[1]}/${partes[0]}/${partes[2]}`;
    
    return data; // Formato ambíguo, manter original
}

// ==============================
//          FEEDBACK
// ==============================
async function submitFeedback(escolha) {
    const feedbackArea = getElement("feedback-area");
    const feedbackMessage = getElement("feedback-message");
    
    if (!feedbackArea || !feedbackMessage) return;
    
    try {
        const response = await fetch("/submit-feedback", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ choice: escolha })
        });
        
        if (!response.ok) throw new Error("Falha ao enviar.");
        
        feedbackMessage.textContent = "Obrigado pelo seu feedback!";
        feedbackMessage.style.color = "#81C784";
        
        feedbackArea.querySelectorAll("button").forEach(button => {
            button.disabled = true;
        });
        
    } catch (error) {
        feedbackMessage.textContent = "Erro ao enviar. Tente novamente.";
        feedbackMessage.style.color = "#ff8a80";
    }
}

// ==============================
//           BLOG
// ==============================
function carregarMaisArtigos() {
    const artigosOcultos = getElements(".artigo-blog:not(.visivel)");
    const quantidadeCarregar = Math.min(4, artigosOcultos.length);
    
    for (let i = 0; i < quantidadeCarregar; i++) {
        artigosOcultos[i].classList.add("visivel");
        artigosVisiveis++;
    }
    
    atualizarContadorArtigos();
    
    if (artigosOcultos.length > 0) {
        artigosOcultos[0].scrollIntoView({ behavior: "smooth", block: "center" });
    }
}

function atualizarContadorArtigos() {
    const contadorArtigos = getElement("contador-artigos");
    if (contadorArtigos) {
        contadorArtigos.textContent = `Mostrando ${artigosVisiveis} de ${totalArtigos} artigos`;
    }
    
    const botaoCarregarMais = document.querySelector(".carregar-mais");
    const mensagemCarregar = document.querySelector(".carregar-mais-container p");
    
    if (artigosVisiveis >= totalArtigos) {
        if (botaoCarregarMais) botaoCarregarMais.style.display = "none";
        if (mensagemCarregar) {
            mensagemCarregar.innerHTML = '<span style="color: var(--cor-sucesso);">✓ Todos os artigos carregados!</span>';
        }
    }
}

function toggleArtigo(artigoId) {
    const artigo = getElement(artigoId);
    if (!artigo) return;
    
    const artigoContainer = artigo.closest(".artigo-blog");
    const resumo = artigoContainer.querySelector(".artigo-resumo");
    const iconeChevron = artigoContainer.querySelector(".fa-chevron-down, .fa-chevron-up");
    
    const isExpandido = artigo.classList.contains("artigo-expandido");
    
    artigo.classList.toggle("artigo-expandido", !isExpandido);
    
    if (resumo) resumo.style.display = isExpandido ? "block" : "none";
    
    if (iconeChevron) {
        iconeChevron.classList.toggle("fa-chevron-up", !isExpandido);
        iconeChevron.classList.toggle("fa-chevron-down", isExpandido);
    }
}

// ==============================
//       COMPARTILHAMENTO
// ==============================
const compartilhamento = {
    whatsapp: (titulo, url) => {
        const texto = encodeURIComponent(`${titulo} - ${url}`);
        window.open(`https://wa.me/?text=${texto}`, "_blank");
    },
    
    facebook: (url) => {
        window.open(`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`, "_blank");
    },
    
    twitter: (titulo, url) => {
        const texto = encodeURIComponent(`${titulo} ${url}`);
        window.open(`https://twitter.com/intent/tweet?text=${texto}`, "_blank");
    },
    
    threads: (titulo, url) => {
        const texto = encodeURIComponent(`${titulo} ${url}`);
        window.open(`https://www.threads.net/intent/post?text=${texto}`, "_blank");
    },
    
    instagram: () => {
        if (confirm("Para compartilhar no Instagram:\n\n1. Abra o Instagram\n2. Crie uma nova publicação ou story\n3. Marque @sorteanalisadaoficial\n4. Use a hashtag #SorteAnalisada\n\nDeseja abrir o Instagram?")) {
            window.open("https://www.instagram.com/sorteanalisadaoficial?igsh=cW8zenNycWVieXF1", "_blank");
        }
    },
    
    tiktok: () => {
        if (confirm("Para compartilhar no TikTok:\n\n1. Abra o TikTok\n2. Crie um vídeo mencionando a Sorte Analisada\n3. Use a hashtag #SorteAnalisada\n4. Marque @sorteanalisadaoficial\n\nDeseja abrir o TikTok?")) {
            window.open("https://www.tiktok.com/@sorteanalisadaoficial?_t=ZM-8zrr5U69ErI&_r=1/", "_blank");
        }
    }
};

// Funções de compartilhamento (mantidas para compatibilidade)
function compartilharWhatsApp(titulo, url) { compartilhamento.whatsapp(titulo, url); }
function compartilharFacebook(url) { compartilhamento.facebook(url); }
function compartilharTwitter(titulo, url) { compartilhamento.twitter(titulo, url); }
function compartilharThreads(titulo, url) { compartilhamento.threads(titulo, url); }
function compartilharInstagram() { compartilhamento.instagram(); }
function compartilharTikTok() { compartilhamento.tiktok(); }

function copiarLink(url, event) {
    navigator.clipboard.writeText(url).then(() => {
        const botao = event?.target?.closest(".share-btn");
        if (botao) {
            const textoOriginal = botao.innerHTML;
            botao.innerHTML = '<i class="fa-solid fa-check"></i> Copiado!';
            botao.style.background = "var(--cor-sucesso)";
            
            setTimeout(() => {
                botao.innerHTML = textoOriginal;
                botao.style.background = "#6c757d";
            }, 2000);
        }
    }).catch(error => {
        console.error("Falha ao copiar:", error);
        
        // Fallback para navegadores antigos
        const textArea = document.createElement("textarea");
        textArea.value = url;
        document.body.appendChild(textArea);
        textArea.select();
        
        try {
            document.execCommand("copy");
            alert("Link copiado!");
        } catch (err) {
            alert("Falha ao copiar. Por favor, copie manualmente: " + url);
        }
        
        document.body.removeChild(textArea);
    });
}

// ==============================
//       CARREGAMENTO DO FOOTER
// ==============================
function carregarFooter() {
    const footerElement = getElement("footer");
    if (footerElement) {
        fetch("/static/partials/footer.html")
            .then(response => response.text())
            .then(html => {
                footerElement.innerHTML = html;
            })
            .catch(error => console.error("Erro ao carregar rodapé:", error));
    }
}

// ==============================
//       EVENT LISTENERS
// ==============================
function configurarEventListeners() {
    // Configurar loteria inicial
    const loteriaSelect = getElement("loteria-select");
    if (loteriaSelect) {
        loteriaAtual = loteriaSelect.value;
        mudarLoteria(loteriaAtual);
        
        loteriaSelect.addEventListener("change", () => mudarLoteria(loteriaSelect.value));
        
        // Select de resultados
        const loteriaSelectResultados = getElement("loteria-select-resultados");
        if (loteriaSelectResultados) {
            loteriaSelectResultados.addEventListener("change", () => {
                mudarLoteriaResultados(loteriaSelectResultados.value);
            });
        }
        
        // Estratégia
        const estrategiaSelect = getElement("estrategia-select");
        if (estrategiaSelect) {
            estrategiaSelect.addEventListener("change", handleEstrategiaChange);
        }
        
        // Botão gerar palpites
        const botaoGerar = getElement("botao-gerar-principal");
        if (botaoGerar) {
            botaoGerar.addEventListener("click", gerarPalpites);
        }
        
        // Botão estatísticas
        const botaoEstatisticas = document.querySelector("#estatisticas .botao-gerar");
        if (botaoEstatisticas) {
            botaoEstatisticas.addEventListener("click", exibirEstatisticas);
        }
    }
}

function configurarEventListenersBlog() {
    // Contador de artigos
    const contadorArtigos = getElement("contador-artigos");
    if (contadorArtigos) {
        contadorArtigos.textContent = `Mostrando ${artigosVisiveis} de ${totalArtigos} artigos`;
        
        // Botão carregar mais
        const botaoCarregarMais = document.querySelector(".carregar-mais");
        if (botaoCarregarMais) {
            botaoCarregarMais.addEventListener("click", carregarMaisArtigos);
        }
        
        // Mostrar artigos iniciais
        getElements(".artigo-blog").forEach((artigo, index) => {
            if (index < artigosVisiveis) {
                artigo.classList.add("visivel");
            }
        });
    }
}

function configurarEventListenersCompartilhamento() {
    // Botões de copiar link
    getElements(".share-btn.copy-link").forEach(botao => {
        botao.addEventListener("click", function(event) {
            const url = botao.dataset.url || window.location.href;
            copiarLink(url, event);
        });
    });
}

// ==============================
//         INICIALIZAÇÃO
// ==============================
document.addEventListener("DOMContentLoaded", function() {
    carregarFooter();
    configurarEventListeners();
    configurarEventListenersBlog();
    configurarEventListenersCompartilhamento();
});