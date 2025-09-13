// ======================================
//             HOME
// ======================================

let loteriaAtual = 'megasena';
const lotteryConfig = {
    'megasena':   {nome: 'Mega-Sena', min_dezenas: 6, max_dezenas: 20, num_bolas: 6, universo: 60},
    'quina':      {nome: 'Quina', min_dezenas: 5, max_dezenas: 15, num_bolas: 5, universo: 80},
    'lotofacil':  {nome: 'Lotofácil', min_dezenas: 15, max_dezenas: 20, num_bolas: 15, universo: 25},
    'diadesorte': {nome: 'Dia de Sorte', min_dezenas: 7, max_dezenas: 15, num_bolas: 7, universo: 31}
};

let graficoMaisSorteados = null, graficoMenosSorteados = null, graficoPrimos = null, graficoParesImpares = null;
let graficoMaisSorteadosRecentes = null, graficoMenosSorteadosRecentes = null; 
let loteriaAtualStats = 'megasena'; 


function mudarLoteria(novaLoteria) {
    loteriaAtual = novaLoteria;
    loteriaAtualStats = novaLoteria; // JÁ EXISTE, MAS REFORÇANDO A LÓGICA

    document.getElementById('loteria-select').value = novaLoteria;

    const config = lotteryConfig[loteriaAtual];
    const displayLoteria = document.getElementById('loteria-selecionada');
    displayLoteria.textContent = config.nome;
    displayLoteria.style.opacity = 1;

    const seletorResultados = document.getElementById('loteria-select-resultados');
    if (seletorResultados) {
        seletorResultados.value = novaLoteria;
    }
    const seletorStats = document.getElementById('loteria-select-stats');
    if (seletorStats) {
        seletorStats.value = novaLoteria; // Garante que o seletor de estatísticas reflita a loteria principal
    }


    document.getElementById('nome-loteria-resultados').textContent = config.nome;
    
    atualizarOpcoesDezenas();
    atualizarOpcoesQuantidade();
    handleEstrategiaChange();
    
    document.getElementById('area-resultados').innerHTML = '';
    
    // Oculta a área de estatísticas e mostra o botão novamente quando a loteria principal muda
    const areaStats = document.getElementById('area-estatisticas');
    if (areaStats) {
        areaStats.style.display = 'none';
        const botaoStats = document.querySelector('#estatisticas .botao-gerar');
        if (botaoStats) {
            botaoStats.style.display = 'block';
            botaoStats.disabled = false;
            botaoStats.innerHTML = 'Estatísticas';
        }
    }
    
    carregarUltimosResultados(novaLoteria);
}




function mudarLoteriaResultados(novaLoteria) {
    const config = lotteryConfig[novaLoteria];
    document.getElementById('nome-loteria-resultados').textContent = config.nome;
    carregarUltimosResultados(novaLoteria);
}

function mudarLoteriaStats(novaLoteria) {
    loteriaAtualStats = novaLoteria;
    exibirEstatisticas(); 
}


function atualizarOpcoesDezenas() {
    const select = document.getElementById('dezenas-select');
    const config = lotteryConfig[loteriaAtual];
    select.innerHTML = '';
    for (let i = config.min_dezenas; i <= config.max_dezenas; i++) {
        const option = document.createElement('option');
        option.value = i;
        option.textContent = `${i} Dezenas`;
        select.appendChild(option);
    }
}

function atualizarOpcoesQuantidade() {
    const select = document.getElementById('quantidade-select');
    select.innerHTML = '';
    for (let i = 1; i <= 10; i++) {
        const option = document.createElement('option');
        option.value = i;
        option.textContent = `${String(i).padStart(2, '0')} ${i > 1 ? 'Jogos' : 'Jogo'}`;
        select.appendChild(option);
    }
}

// ... dentro da função handleEstrategiaChange() ...
function handleEstrategiaChange() {
    const estrategia = document.getElementById('estrategia-select').value;
    const dezenasSelect = document.getElementById('dezenas-select');
    const quantidadeSelect = document.getElementById('quantidade-select');
    const ancoraInput = document.getElementById('numeros-ancora');
    const config = lotteryConfig[loteriaAtual];

    if (estrategia === 'montecarlo' || estrategia === 'sorteanalisadapremium') {
        dezenasSelect.value = config.num_bolas;
        dezenasSelect.disabled = true;
        quantidadeSelect.value = 1;
        quantidadeSelect.disabled = true;
        ancoraInput.value = '';
        ancoraInput.disabled = true;
    } else { // 'geral', 'quentes', 'mistas', 'frias', 'aleatorio', 'juntoemisturado'
        dezenasSelect.disabled = false;
        quantidadeSelect.disabled = false;
        ancoraInput.disabled = false;
    }
}

function setGeradorEstado(desabilitar) {
    isRequestInProgress = desabilitar;
    document.getElementById('botao-gerar-principal').disabled = desabilitar;
    document.querySelectorAll('.seletor-custom, #numeros-ancora').forEach(el => el.disabled = desabilitar);
}

function renderizarJogos(jogosArray, areaResultados) {
    areaResultados.innerHTML = '<h2>Boa sorte!</h2>';
    const meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];

    jogosArray.forEach(linha => {
        const jogoContainer = document.createElement('div');
        jogoContainer.className = 'jogo';
        
        const numerosContainer = document.createElement('div');
        numerosContainer.className = 'numeros-container';
        
        linha.trim().split(/\s+/).forEach(num => {
            const span = document.createElement('span');
            span.className = 'numero';
            span.textContent = num;
            numerosContainer.appendChild(span);
        });

        if (loteriaAtual === 'diadesorte') {
            const mesSorteado = meses[Math.floor(Math.random() * meses.length)];
            const spanMes = document.createElement('span');
            spanMes.textContent = `| Mês: ${mesSorteado}`;
            spanMes.style.cssText = 'font-weight:bold; margin-left:15px; font-size: 1.2rem;';
            numerosContainer.appendChild(spanMes);
        }
        
        const copyButton = document.createElement('button');
        copyButton.className = 'botao-copiar';
        copyButton.innerHTML = '<i class="fa-regular fa-copy"></i>';
        copyButton.title = 'Copiar números';
        copyButton.onclick = function() { copiarNumeros(this); };

        jogoContainer.appendChild(numerosContainer);
        jogoContainer.appendChild(copyButton);
        areaResultados.appendChild(jogoContainer);
    });

    const instrucao = document.createElement('p');
    instrucao.className = 'instrucao-aposta';
    instrucao.textContent = '* Importante: O Sorte Analisada é um gerador de números: com análises estatísticas e números aleatórios. É uma plataforma independente, destinada exclusivamente ao entretenimento, As sugestões geradas não garantem ganhos e não aumentam a probabilidade de acerto. Jogue de forma consciente e responsável. O acesso ao site é gratuíto. Não comercializamos produtos Lotéricos! Caso queira concorrer com os números gerados no site, você precisa registrar em uma aposta oficial, em qualquer agência lotérica ou no site de apostas da Caixa Economica Federal®, por sua conta e riscos. Boa sorte!';
    areaResultados.appendChild(instrucao);
}

async function gerarPalpites() {
    if (isRequestInProgress) return;
    
    const areaResultados = document.getElementById('area-resultados');
    const estrategia = document.getElementById('estrategia-select').value;
    const dezenas = document.getElementById('dezenas-select').value;
    const quantidade = document.getElementById('quantidade-select').value;
    const numerosAncora = document.getElementById('numeros-ancora').value;
    
    setGeradorEstado(true);
    areaResultados.innerHTML = '<div class="spinner"></div>';
    
    try {
        let url = '';
        if (estrategia === 'montecarlo') {
            url = `/get-monte-carlo-game?loteria=${loteriaAtual}&ancora=${numerosAncora}`;
        } else if (estrategia === 'sorteanalisadapremium') {
            url = `/get-sorte-analisada-premium-game?loteria=${loteriaAtual}`;
        } else {
            url = `/get-games/${quantidade}?loteria=${loteriaAtual}&estrategia=${estrategia}&dezenas=${dezenas}&ancora=${numerosAncora}`;
        }

        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`Erro na comunicação com o servidor: ${response.statusText}`);
        }
        
        const data = await response.json();
        if (data.error) {
            throw new Error(`Erro no servidor: ${data.error}`);
        }

        const jogosParaRenderizar = (estrategia === 'montecarlo' || estrategia === 'sorteanalisadapremium') ? [data.jogo] : data;
        renderizarJogos(jogosParaRenderizar, areaResultados);

    } catch (error) {
        console.error('Detalhes do erro:', error);
        areaResultados.innerHTML = `<p style="color: #ff8a80;">Falha na conexão. Por favor, tente novamente em alguns segundos.</p>`;
    } finally {
            if (estrategia === 'montecarlo' || estrategia === 'sorteanalisadapremium') {
            let cooldownTime = estrategia === 'sorteanalisadapremium' ? 20 : 10;
            let countdown = cooldownTime;
            const botao = document.getElementById('botao-gerar-principal');
            botao.innerHTML = `Aguarde ${countdown}s...`;
            
            const interval = setInterval(() => {
                countdown--;
                if (countdown > 0) {
                    botao.innerHTML = `Aguarde ${countdown}s...`;
                } else {
                    clearInterval(interval);
                    botao.innerHTML = 'Gerar Palpites';
                    setGeradorEstado(false);
                    handleEstrategiaChange();
                }
            }, 1000);
        } else {
            setGeradorEstado(false);
            handleEstrategiaChange();
        }
    }
}


// ... (dentro da função exibirEstatisticas(), logo no início) ...
async function exibirEstatisticas() {
    const botao = document.querySelector('#estatisticas .botao-gerar');
    if (isRequestInProgress || (botao && botao.disabled)) return;

    const areaStats = document.getElementById('area-estatisticas');
    isRequestInProgress = true;
    if (botao) {
        botao.disabled = true;
        botao.innerHTML = '<div class="spinner" style="width:25px;height:25px;margin:0 auto;"></div>';
    }
    
    try {
        // As requisições devem usar loteriaAtualStats
        const [responseGeral, responseRecente] = await Promise.all([
            fetch(`/get-stats?loteria=${loteriaAtualStats}`), // <-- Alterado aqui
            fetch(`/get-stats-recentes?loteria=${loteriaAtualStats}`) // <-- Alterado aqui
        ]);

        if (!responseGeral.ok) throw new Error('Falha ao buscar dados gerais do servidor.');
        if (!responseRecente.ok) throw new Error('Falha ao buscar dados recentes do servidor.');

        const dataGeral = await responseGeral.json();
        const dataRecente = await responseRecente.json();

        if (dataGeral.error || !dataGeral.frequencia || !dataGeral.stats_primos || !dataGeral.stats_pares) 
            throw new Error(dataGeral.error || 'Os dados gerais recebidos são inválidos.');
        if (dataRecente.error || !dataRecente.frequencia_recente) 
            throw new Error(dataRecente.error || 'Os dados recentes recebidos são inválidos.');

        const nomeLoteria = lotteryConfig[loteriaAtualStats].nome; // <-- Alterado aqui
        document.getElementById('ultimo-concurso-info').innerHTML = `Análise da ${nomeLoteria} baseada até o concurso ${dataGeral.ultimo_concurso}`;
        areaStats.style.display = 'block';

        // Destruir gráficos existentes
        [graficoMaisSorteados, graficoMenosSorteados, graficoPrimos, graficoParesImpares,
         graficoMaisSorteadosRecentes, graficoMenosSorteadosRecentes].forEach(g => { if(g) g.destroy(); });

        const corTexto = '#FFFDE7', corGrid = 'rgba(255, 255, 255, 0.2)';
        
        const chartOptions = { 
            scales: { 
                y: { ticks: { color: corTexto }, grid: { color: corGrid } }, 
                x: { ticks: { color: corTexto }, grid: { color: 'transparent' } } 
            }, 
            plugins: { 
                legend: { 
                    labels: { color: corTexto },
                    onClick: null
                } 
            } 
        };

        // Gráficos Gerais (existentes)
        const maisSorteados = [...dataGeral.frequencia].sort((a, b) => b.frequencia - a.frequencia).slice(0, 10);
        graficoMaisSorteados = new Chart(document.getElementById('grafico-mais-sorteados').getContext('2d'), { type: 'bar', data: { labels: maisSorteados.map(i => `Nº ${i.numero}`), datasets: [{ label: 'Vezes Sorteado', data: maisSorteados.map(i => i.frequencia), backgroundColor: '#FFD700' }] }, options: chartOptions });
        
        const menosSorteados = [...dataGeral.frequencia].sort((a, b) => a.frequencia - b.frequencia).slice(0, 10);
        graficoMenosSorteados = new Chart(document.getElementById('grafico-menos-sorteados').getContext('2d'), { type: 'bar', data: { labels: menosSorteados.map(i => `Nº ${i.numero}`), datasets: [{ label: 'Vezes Sorteado', data: menosSorteados.map(i => i.frequencia), backgroundColor: '#90CAF9' }] }, options: chartOptions });
        
        const labelsPrimos = Object.keys(dataGeral.stats_primos).sort((a,b) => parseInt(a)-parseInt(b)).map(k => `${k} Primos`);
        const dataPrimos = Object.keys(dataGeral.stats_primos).sort((a,b) => parseInt(a)-parseInt(b)).map(k => dataGeral.stats_primos[k]);
        graficoPrimos = new Chart(document.getElementById('grafico-primos').getContext('2d'), { type: 'bar', data: { labels: labelsPrimos, datasets: [{ label: 'Sorteios', data: dataPrimos, backgroundColor: '#81C784' }] }, options: chartOptions });
        
        const numBolas = lotteryConfig[loteriaAtualStats].num_bolas; // <-- Alterado aqui
        const labelsPares = Object.keys(dataGeral.stats_pares).sort((a,b) => parseInt(a)-parseInt(b)).map(k => `${k} Pares / ${numBolas - parseInt(k)} Ímpares`);
        const dataPares = Object.keys(dataGeral.stats_pares).sort((a,b) => parseInt(a)-parseInt(b)).map(k => dataGeral.stats_pares[k]);
        graficoParesImpares = new Chart(document.getElementById('grafico-pares-impares').getContext('2d'), { type: 'bar', data: { labels: labelsPares, datasets: [{ label: 'Sorteios', data: dataPares, backgroundColor: '#FF8A65' }] }, options: chartOptions });
        
        // NOVOS GRÁFICOS: Mais e Menos Sorteadas (Últimos 100)
        const maisSorteadosRecentes = [...dataRecente.frequencia_recente].sort((a, b) => b.frequencia - a.frequencia).slice(0, 10);
        graficoMaisSorteadosRecentes = new Chart(document.getElementById('grafico-mais-sorteados-recentes').getContext('2d'), { type: 'bar', data: { labels: maisSorteadosRecentes.map(i => `Nº ${i.numero}`), datasets: [{ label: 'Vezes Sorteado (Últimos 100)', data: maisSorteadosRecentes.map(i => i.frequencia), backgroundColor: '#FFECB3' }] }, options: chartOptions });

        const menosSorteadosRecentes = [...dataRecente.frequencia_recente].sort((a, b) => a.frequencia - b.frequencia).slice(0, 10);
        graficoMenosSorteadosRecentes = new Chart(document.getElementById('grafico-menos-sorteados-recentes').getContext('2d'), { type: 'bar', data: { labels: menosSorteadosRecentes.map(i => `Nº ${i.numero}`), datasets: [{ label: 'Vezes Sorteado (Últimos 100)', data: menosSorteadosRecentes.map(i => i.frequencia), backgroundColor: '#BBDEFB' }] }, options: chartOptions });

        botao.style.display = 'none';

     } catch (error) {
        areaStats.innerHTML = `<p style="color: #ff8a80;">${error.message}</p>`;
        areaStats.style.display = 'block';
        if (botao) {
            botao.innerHTML = 'Estatísticas';
            botao.disabled = false;
        }
    } finally {
        isRequestInProgress = false;
    }
}


async function submitFeedback(choice) {
    const feedbackArea = document.getElementById('feedback-area');
    const messageEl = document.getElementById('feedback-message');
    try {
        const response = await fetch('/submit-feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ choice: choice })
        });
        if (!response.ok) throw new Error('Falha ao enviar.');

        messageEl.textContent = 'Obrigado pelo seu feedback!';
        messageEl.style.color = '#81C784';
        feedbackArea.querySelectorAll('button').forEach(btn => btn.disabled = true);
    } catch (error) {
        messageEl.textContent = 'Erro ao enviar. Tente novamente.';
        messageEl.style.color = '#ff8a80';
    }
}

async function carregarUltimosResultados(loteria) {
    const container = document.getElementById('lista-ultimos-resultados');
    container.innerHTML = '<div class="spinner"></div>';

    try {
        const response = await fetch(`/get-ultimos-resultados?loteria=${loteria}`);
        if (!response.ok) {
            throw new Error('Falha ao carregar os resultados.');
        }
        const resultados = await response.json();

        if (resultados.error) {
            throw new Error(resultados.error);
        }

        if (resultados.length === 0) {
            container.innerHTML = '<p>Nenhum resultado encontrado para esta loteria.</p>';
            return;
        }

        let html = '';
        resultados.forEach(res => {
            let statusHtml = '';
            if (res.acumulou) {
                let valorHtml = res.valor_acumulado
                    ? `<div class="valor-acumulado">Prêmio estimado: R$ ${res.valor_acumulado.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</div>`
                    : '';
                statusHtml = `<span class="status-acumulou">ACUMULOU</span>${valorHtml}`;
            } else {
                const ganhadorLabel = res.ganhadores > 1 ? 'Ganhadores' : 'Ganhador';
                statusHtml = `<span class="status-ganhador">${res.ganhadores} ${ganhadorLabel}</span>`;
            }


            let mesDaSorteHtml = '';
            if (loteria === 'diadesorte' && res.mes_sorte) {
                    mesDaSorteHtml = `<div class="resultado-mes">Mês da Sorte: <strong>${res.mes_sorte}</strong></div>`;
            }

            // --- INÍCIO DA MODIFICAÇÃO PARA FORMATAR A DATA ---
            let dataFormatada = '';
            if (res.data) {
                const partesData = res.data.split('/'); // Divide a string "MM/DD/YYYY"
                if (partesData.length === 3) {
                    // Reorganiza para "DD/MM/YYYY"
                    dataFormatada = `${partesData[1]}/${partesData[0]}/${partesData[2]}`;
                } else {
                    dataFormatada = res.data; // Mantém o original se não conseguir formatar
                }
            }
            // --- FIM DA MODIFICAÇÃO ---

            html += `
                <div class="resultado-item">
                    <div class="resultado-header">
                        <span class="resultado-concurso">Concurso ${res.concurso}</span>
                        <span class="resultado-data">${dataFormatada}</span>
                    </div>
                    <div class="resultado-dezenas">${res.dezenas}</div>
                    ${mesDaSorteHtml}
                    <div class="resultado-status">${statusHtml}</div>
                </div>
            `;
        });

        container.innerHTML = html;

    } catch (error) {
        console.error('Erro ao carregar últimos resultados:', error);
        container.innerHTML = `<p style="color: #ff8a80;">Não foi possível carregar os resultados. Tente novamente mais tarde.</p>`;
    }
}

document.addEventListener('DOMContentLoaded', (event) => {
    // --- HOME ---
    const seletorPrincipal = document.getElementById('loteria-select');
    if (seletorPrincipal) {
        loteriaAtual = seletorPrincipal.value;
        mudarLoteria(loteriaAtual);

        // Atribui eventos aos seletores
        seletorPrincipal.addEventListener('change', () => mudarLoteria(seletorPrincipal.value));
        const seletorResultados = document.getElementById('loteria-select-resultados');
        if (seletorResultados) {
            seletorResultados.addEventListener('change', () => mudarLoteriaResultados(seletorResultados.value));
        }
        document.getElementById('estrategia-select')?.addEventListener('change', handleEstrategiaChange);
        document.getElementById('botao-gerar-principal')?.addEventListener('click', gerarPalpites);
    }

    // NOVO: Chamar exibirEstatisticas na carga da página para a loteria padrão
    exibirEstatisticas(); // Vai usar loteriaAtualStats, que deve estar sincronizada
});


document.addEventListener('DOMContentLoaded', () => {
    const seletorStats = document.getElementById('loteria-select-stats');
    if (seletorStats) {
        // Garante que o seletor de stats reflita a loteria atual quando a página carrega
        seletorStats.value = loteriaAtual; // Use loteriaAtual aqui, pois ela é definida primeiro
        // NÃO CHAME exibirEstatisticas aqui novamente, pois já foi chamado acima
    }
});


