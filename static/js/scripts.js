// ======================================
//             SEÇÃO COMUM
// ======================================

let isRequestInProgress = false;

// Função para copiar números genérica
function copiarNumeros(buttonEl) {
    const jogoContainer = buttonEl.closest('.jogo');
    
    if (!jogoContainer) {
        const textoParaCopiar = buttonEl.getAttribute('data-copy-text');
        if (textoParaCopiar) {
            navigator.clipboard.writeText(textoParaCopiar).then(() => {
                const originalText = buttonEl.innerHTML;
                buttonEl.innerHTML = '<i class="fa-solid fa-check"></i> Copiado!';
                buttonEl.style.background = 'var(--cor-sucesso)';
                setTimeout(() => {
                    buttonEl.innerHTML = originalText;
                    buttonEl.style.removeProperty('background');
                }, 2000);
            }).catch(err => {
                console.error('Falha ao copiar:', err);
                alert('Falha ao copiar. Por favor, copie manualmente: ' + textoParaCopiar);
            });
            return;
        }
    }

    const numeros = [...jogoContainer.querySelectorAll('.numero')].map(n => n.textContent).join(' ');
    
    navigator.clipboard.writeText(numeros).then(() => {
        const originalIcon = buttonEl.innerHTML;
        buttonEl.innerHTML = '<i class="fa-solid fa-check"></i>';
        setTimeout(() => {
            buttonEl.innerHTML = originalIcon;
        }, 2000);
    }).catch(err => {
        console.error('Falha ao copiar números: ', err);
    });
}

// Carregar footer
if (document.getElementById("footer")) {
    fetch("/static/partials/footer.html")
        .then(response => response.text())
        .then(data => {
            document.getElementById("footer").innerHTML = data;
        })
        .catch(err => console.error("Erro ao carregar rodapé:", err));
}

// ======================================
//             SEÇÃO HOME
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
let carregandoResultados = false;

function mudarLoteria(novaLoteria) {
    loteriaAtual = novaLoteria;
    const config = lotteryConfig[loteriaAtual];
    const displayLoteria = document.getElementById('loteria-selecionada');
    
    if (displayLoteria) {
        displayLoteria.textContent = config.nome;
        displayLoteria.style.opacity = 1;
    }

    const seletorResultados = document.getElementById('loteria-select-resultados');
    if (seletorResultados) {
        seletorResultados.value = novaLoteria;
    }

    const nomeLoteriaResultados = document.getElementById('nome-loteria-resultados');
    if (nomeLoteriaResultados) {
        nomeLoteriaResultados.textContent = config.nome;
    }
    
    atualizarOpcoesDezenas();
    atualizarOpcoesQuantidade();
    handleEstrategiaChange();
    
    const areaResultados = document.getElementById('area-resultados');
    if (areaResultados) {
        areaResultados.innerHTML = '';
    }
    
    const areaStats = document.getElementById('area-estatisticas');
    if (areaStats) {
        areaStats.style.display = 'none';
    }
    
    const botaoStats = document.querySelector('#estatisticas .botao-gerar');
    if (botaoStats) {
        botaoStats.style.display = 'block';
        botaoStats.disabled = false;
        botaoStats.innerHTML = 'Estatísticas';
    }
    
    carregarUltimosResultados(novaLoteria);
}

function mudarLoteriaResultados(novaLoteria) {
    const config = lotteryConfig[novaLoteria];
    const nomeLoteriaResultados = document.getElementById('nome-loteria-resultados');
    if (nomeLoteriaResultados) {
        nomeLoteriaResultados.textContent = config.nome;
    }
    carregarUltimosResultados(novaLoteria);
}

function atualizarOpcoesDezenas() {
    const select = document.getElementById('dezenas-select');
    if (!select) return;
    
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
    if (!select) return;
    
    select.innerHTML = '';
    for (let i = 1; i <= 10; i++) {
        const option = document.createElement('option');
        option.value = i;
        option.textContent = `${String(i).padStart(2, '0')} ${i > 1 ? 'Jogos' : 'Jogo'}`;
        select.appendChild(option);
    }
}

function handleEstrategiaChange() {
    const estrategiaSelect = document.getElementById('estrategia-select');
    const dezenasSelect = document.getElementById('dezenas-select');
    const quantidadeSelect = document.getElementById('quantidade-select');
    const ancoraInput = document.getElementById('numeros-ancora');
    
    if (!estrategiaSelect || !dezenasSelect || !quantidadeSelect || !ancoraInput) return;
    
    const estrategia = estrategiaSelect.value;
    const config = lotteryConfig[loteriaAtual];

    if (estrategia === 'montecarlo' || estrategia === 'sorteanalisadapremium') {
        dezenasSelect.value = config.num_bolas;
        dezenasSelect.disabled = true;
        quantidadeSelect.value = 1;
        quantidadeSelect.disabled = true;
        ancoraInput.value = '';
        ancoraInput.disabled = true;
    } else {
        dezenasSelect.disabled = false;
        quantidadeSelect.disabled = false;
        ancoraInput.disabled = false;
    }
}

function setGeradorEstado(desabilitar) {
    isRequestInProgress = desabilitar;
    const botaoGerar = document.getElementById('botao-gerar-principal');
    if (botaoGerar) botaoGerar.disabled = desabilitar;
    
    document.querySelectorAll('.seletor-custom, #numeros-ancora').forEach(el => {
        if (el) el.disabled = desabilitar;
    });
}

function renderizarJogos(jogosArray, areaResultados) {
    if (!areaResultados) return;
    
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
    instrucao.textContent = 'Caso queira concorrer com os números gerados no site, você precisa registra-lo em uma aposta oficial, em qualquer agência lotérica ou no site de apostas da Caixa Econômica Federal®, por sua conta e riscos. Boa sorte!';
    areaResultados.appendChild(instrucao);
}

async function gerarPalpites() {
    if (isRequestInProgress) return;
    
    const areaResultados = document.getElementById('area-resultados');
    const estrategiaSelect = document.getElementById('estrategia-select');
    const dezenasSelect = document.getElementById('dezenas-select');
    const quantidadeSelect = document.getElementById('quantidade-select');
    const ancoraInput = document.getElementById('numeros-ancora');
    
    if (!areaResultados || !estrategiaSelect || !dezenasSelect || !quantidadeSelect || !ancoraInput) return;
    
    const estrategia = estrategiaSelect.value;
    const dezenas = dezenasSelect.value;
    const quantidade = quantidadeSelect.value;
    const numerosAncora = ancoraInput.value;
    
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
            if (botao) {
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
            }
        } else {
            setGeradorEstado(false);
            handleEstrategiaChange();
        }
    }
}

async function exibirEstatisticas() {
    const botao = document.querySelector('#estatisticas .botao-gerar');
    if (isRequestInProgress || !botao || botao.disabled) return;
    
    const areaStats = document.getElementById('area-estatisticas');
    isRequestInProgress = true;
    botao.disabled = true;
    botao.innerHTML = '<div class="spinner" style="width: 25px; height: 25px; margin: 0 auto;"></div> Carregando...';
    
    try {
        const [responseGeral, responseRecente] = await Promise.all([
            fetch(`/get-stats?loteria=${loteriaAtual}`),
            fetch(`/get-stats-recentes?loteria=${loteriaAtual}`)
        ]);

        if (!responseGeral.ok) throw new Error('Falha ao buscar dados gerais do servidor.');
        if (!responseRecente.ok) throw new Error('Falha ao buscar dados recentes do servidor.');

        const dataGeral = await responseGeral.json();
        const dataRecente = await responseRecente.json();

        if (dataGeral.error || !dataGeral.frequencia || !dataGeral.stats_primos || !dataGeral.stats_pares) 
            throw new Error(dataGeral.error || 'Os dados gerais recebidos são inválidos.');
        if (dataRecente.error || !dataRecente.frequencia_recente) 
            throw new Error(dataRecente.error || 'Os dados recentes recebidos são inválidos.');

        const nomeLoteria = lotteryConfig[loteriaAtual].nome;
        const ultimoConcursoInfo = document.getElementById('ultimo-concurso-info');
        if (ultimoConcursoInfo) {
            ultimoConcursoInfo.innerHTML = `Análise da ${nomeLoteria}: até o concurso ${dataGeral.ultimo_concurso}`;
        }
        
        if (areaStats) {
            areaStats.style.display = 'block';
        }

        // Destruir gráficos existentes
        [graficoMaisSorteados, graficoMenosSorteados, graficoPrimos, graficoParesImpares,
         graficoMaisSorteadosRecentes, graficoMenosSorteadosRecentes].forEach(g => { 
             if(g) g.destroy(); 
         });

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

        // Gráficos Gerais
        const maisSorteados = [...dataGeral.frequencia].sort((a, b) => b.frequencia - a.frequencia).slice(0, 10);
        const ctxMaisSorteados = document.getElementById('grafico-mais-sorteados');
        if (ctxMaisSorteados) {
            graficoMaisSorteados = new Chart(ctxMaisSorteados.getContext('2d'), { 
                type: 'bar', 
                data: { 
                    labels: maisSorteados.map(i => `Nº ${i.numero}`), 
                    datasets: [{ 
                        label: 'Vezes Sorteado', 
                        data: maisSorteados.map(i => i.frequencia), 
                        backgroundColor: '#FFD700' 
                    }] 
                }, 
                options: chartOptions 
            });
        }
        
        const menosSorteados = [...dataGeral.frequencia].sort((a, b) => a.frequencia - b.frequencia).slice(0, 10);
        const ctxMenosSorteados = document.getElementById('grafico-menos-sorteados');
        if (ctxMenosSorteados) {
            graficoMenosSorteados = new Chart(ctxMenosSorteados.getContext('2d'), { 
                type: 'bar', 
                data: { 
                    labels: menosSorteados.map(i => `Nº ${i.numero}`), 
                    datasets: [{ 
                        label: 'Vezes Sorteado', 
                        data: menosSorteados.map(i => i.frequencia), 
                        backgroundColor: '#90CAF9' 
                    }] 
                }, 
                options: chartOptions 
            });
        }
        
        const labelsPrimos = Object.keys(dataGeral.stats_primos).sort((a,b) => parseInt(a)-parseInt(b)).map(k => `${k} Primos`);
        const dataPrimos = Object.keys(dataGeral.stats_primos).sort((a,b) => parseInt(a)-parseInt(b)).map(k => dataGeral.stats_primos[k]);
        const ctxPrimos = document.getElementById('grafico-primos');
        if (ctxPrimos) {
            graficoPrimos = new Chart(ctxPrimos.getContext('2d'), { 
                type: 'bar', 
                data: { 
                    labels: labelsPrimos, 
                    datasets: [{ 
                        label: 'Sorteios', 
                        data: dataPrimos, 
                        backgroundColor: '#81C784' 
                    }] 
                }, 
                options: chartOptions 
            });
        }
        
        const numBolas = lotteryConfig[loteriaAtual].num_bolas;
        const labelsPares = Object.keys(dataGeral.stats_pares).sort((a,b) => parseInt(a)-parseInt(b)).map(k => `${k} Pares / ${numBolas - parseInt(k)} Ímpares`);
        const dataPares = Object.keys(dataGeral.stats_pares).sort((a,b) => parseInt(a)-parseInt(b)).map(k => dataGeral.stats_pares[k]);
        const ctxPares = document.getElementById('grafico-pares-impares');
        if (ctxPares) {
            graficoParesImpares = new Chart(ctxPares.getContext('2d'), { 
                type: 'bar', 
                data: { 
                    labels: labelsPares, 
                    datasets: [{ 
                        label: 'Sorteios', 
                        data: dataPares, 
                        backgroundColor: '#FF8A65' 
                    }] 
                }, 
                options: chartOptions 
            });
        }
        
        // Gráficos Recentes
        const maisSorteadosRecentes = [...dataRecente.frequencia_recente].sort((a, b) => b.frequencia - a.frequencia).slice(0, 10);
        const ctxMaisSorteadosRecentes = document.getElementById('grafico-mais-sorteados-recentes');
        if (ctxMaisSorteadosRecentes) {
            graficoMaisSorteadosRecentes = new Chart(ctxMaisSorteadosRecentes.getContext('2d'), { 
                type: 'bar', 
                data: { 
                    labels: maisSorteadosRecentes.map(i => `Nº ${i.numero}`), 
                    datasets: [{ 
                        label: 'Vezes Sorteado (Últimos 100)', 
                        data: maisSorteadosRecentes.map(i => i.frequencia), 
                        backgroundColor: '#FFECB3' 
                    }] 
                }, 
                options: chartOptions 
            });
        }

        const menosSorteadosRecentes = [...dataRecente.frequencia_recente].sort((a, b) => a.frequencia - b.frequencia).slice(0, 10);
        const ctxMenosSorteadosRecentes = document.getElementById('grafico-menos-sorteados-recentes');
        if (ctxMenosSorteadosRecentes) {
            graficoMenosSorteadosRecentes = new Chart(ctxMenosSorteadosRecentes.getContext('2d'), { 
                type: 'bar', 
                data: { 
                    labels: menosSorteadosRecentes.map(i => `Nº ${i.numero}`), 
                    datasets: [{ 
                        label: 'Vezes Sorteado (Últimos 100)', 
                        data: menosSorteadosRecentes.map(i => i.frequencia), 
                        backgroundColor: '#BBDEFB' 
                    }] 
                }, 
                options: chartOptions 
            });
        }
        
        if (botao) {
            botao.style.display = 'none';
        }

    } catch (error) {
        console.error('Erro ao carregar estatísticas:', error);
        if (areaStats) {
            areaStats.innerHTML = `<p style="color: #ff8a80;">${error.message}</p>`;
            areaStats.style.display = 'block';
        }
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
    
    if (!feedbackArea || !messageEl) return;
    
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
    if (carregandoResultados) return;
    carregandoResultados = true;
    
    const container = document.getElementById('lista-ultimos-resultados');
    if (!container) {
        carregandoResultados = false;
        return;
    }
    
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

            let dataFormatada = '';
            if (res.data) {
                const partesData = res.data.split('/');
                if (partesData.length === 3) {
                    dataFormatada = `${partesData[1]}/${partesData[0]}/${partesData[2]}`;
                } else {
                    dataFormatada = res.data;
                }
            }

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
    } finally {
        carregandoResultados = false;
    }
} 

// ======================================
//             SEÇÃO BLOG
// ======================================

let artigosVisiveis = 5;
const totalArtigos = 9;

function carregarMaisArtigos() {
    const artigos = document.querySelectorAll('.artigo-blog:not(.visivel)');
    const proximosArtigos = Math.min(4, artigos.length);
    
    for (let i = 0; i < proximosArtigos; i++) {
        artigos[i].classList.add('visivel');
        artigosVisiveis++;
    }
    
    const contadorArtigos = document.getElementById('contador-artigos');
    if (contadorArtigos) {
        contadorArtigos.textContent = `Mostrando ${artigosVisiveis} de ${totalArtigos} artigos`;
    }
    
    const carregarMaisBtn = document.querySelector('.carregar-mais');
    const carregarMaisContainer = document.querySelector('.carregar-mais-container p');
    
    if (artigosVisiveis >= totalArtigos) {
        if (carregarMaisBtn) carregarMaisBtn.style.display = 'none';
        if (carregarMaisContainer) {
            carregarMaisContainer.innerHTML = '<span style="color: var(--cor-sucesso);">✓ Todos os artigos carregados!</span>';
        }
    }
    
    if (artigos.length > 0) {
        artigos[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

function toggleArtigo(artigoId) {
    const conteudo = document.getElementById(artigoId);
    if (!conteudo) return;
    
    const artigoPai = conteudo.closest('.artigo-blog');
    const resumo = artigoPai.querySelector('.artigo-resumo');
    const icone = artigoPai.querySelector('.fa-chevron-down, .fa-chevron-up');

    if (conteudo.classList.contains('artigo-expandido')) {
        conteudo.classList.remove('artigo-expandido');
        if (resumo) resumo.style.display = 'block';
        if (icone) {
            icone.classList.remove('fa-chevron-up');
            icone.classList.add('fa-chevron-down');
        }
    } else {
        conteudo.classList.add('artigo-expandido');
        if (resumo) resumo.style.display = 'none';
        if (icone) {
            icone.classList.remove('fa-chevron-down');
            icone.classList.add('fa-chevron-up');
        }
    }
}

// ============== FUNÇÕES DE COMPARTILHAMENTO ============== 
function compartilharWhatsApp(titulo, url) {
    const texto = encodeURIComponent(`${titulo} - ${url}`);
    window.open(`https://wa.me/?text=${texto}`, '_blank');
}

function compartilharFacebook(url) {
    window.open(`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`, '_blank');
}

function compartilharTwitter(texto, url) {
    const tweet = encodeURIComponent(`${texto} ${url}`);
    window.open(`https://twitter.com/intent/tweet?text=${tweet}`, '_blank');
}

function compartilharThreads(texto, url) {
    const thread = encodeURIComponent(`${texto} ${url}`);
    window.open(`https://www.threads.net/intent/post?text=${thread}`, '_blank');
}

function compartilharInstagram() {
    window.open('https://www.instagram.com/sorteanalisadaoficial/', '_blank');
}

function compartilharTikTok() {
    window.open('https://www.tiktok.com/upload', '_blank');
}

function copiarLink(url, event) {
    navigator.clipboard.writeText(url).then(() => {
        const btn = event.target.closest('.share-btn');
        if (btn) {
            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fa-solid fa-check"></i> Copiado!';
            btn.style.background = 'var(--cor-sucesso)';
            
            setTimeout(() => {
                btn.innerHTML = originalText;
                btn.style.background = '#6c757d';
            }, 2000);
        }
    }).catch((err) => {
        console.error('Falha ao copiar:', err);
        // Fallback para navegadores mais antigos
        const textArea = document.createElement('textarea');
        textArea.value = url;
        document.body.appendChild(textArea);
        textArea.select();
        try {
            document.execCommand('copy');
            alert('Link copiado!');
        } catch (fallbackErr) {
            alert('Falha ao copiar. Por favor, copie manualmente: ' + url);
        }
        document.body.removeChild(textArea);
    });
}

// ======================================
//             INICIALIZAÇÃO
// ======================================

document.addEventListener('DOMContentLoaded', (event) => {
    // --- HOME ---
    const seletorPrincipal = document.getElementById('loteria-select');
    if (seletorPrincipal) {
        loteriaAtual = seletorPrincipal.value; 
        mudarLoteria(loteriaAtual); 

        seletorPrincipal.addEventListener('change', () => mudarLoteria(seletorPrincipal.value));
        
        const seletorResultados = document.getElementById('loteria-select-resultados');
        if (seletorResultados) {
            seletorResultados.addEventListener('change', () => mudarLoteriaResultados(seletorResultados.value));
        }
        
        const estrategiaSelect = document.getElementById('estrategia-select');
        if (estrategiaSelect) {
            estrategiaSelect.addEventListener('change', handleEstrategiaChange);
        }
        
        const botaoGerar = document.getElementById('botao-gerar-principal');
        if (botaoGerar) {
            botaoGerar.addEventListener('click', gerarPalpites);
        }
        
        const botaoStats = document.querySelector('#estatisticas .botao-gerar');
        if (botaoStats) {
            botaoStats.addEventListener('click', exibirEstatisticas);
        }
    }
    
    // --- BLOG ---
    const contadorArtigos = document.getElementById('contador-artigos');
    if (contadorArtigos) {
        contadorArtigos.textContent = `Mostrando ${artigosVisiveis} de ${totalArtigos} artigos`;
        
        const carregarMaisBtn = document.querySelector('.carregar-mais');
        if (carregarMaisBtn) {
            carregarMaisBtn.addEventListener('click', carregarMaisArtigos);
        }

        // Garante que os 5 primeiros artigos estejam visíveis
        document.querySelectorAll('.artigo-blog').forEach((artigo, index) => {
            if (index < artigosVisiveis) {
                artigo.classList.add('visivel');
            }
        });
    }

    // Adiciona listener para botões de copiar link
    document.querySelectorAll('.share-btn.copy-link').forEach(btn => {
        btn.addEventListener('click', (e) => {
            if (btn.dataset.url) {
                copiarLink(btn.dataset.url, e);
            }
        });
    });
});
