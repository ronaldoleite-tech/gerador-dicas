// ======================================
//             SEÇÃO COMUM
// ======================================

let isRequestInProgress = false;

// Função para copiar números genérica
function copiarNumeros(buttonEl) {
    const jogoContainer = buttonEl.closest('.jogo'); // Pode ser usado no home para os jogos gerados
    if (!jogoContainer) { // Adicionado para lidar com o caso do blog ou outras áreas sem .jogo
        const textoParaCopiar = buttonEl.getAttribute('data-copy-text');
        if (textoParaCopiar) {
            navigator.clipboard.writeText(textoParaCopiar).then(() => {
                const originalText = buttonEl.innerHTML;
                buttonEl.innerHTML = '<i class="fa-solid fa-check"></i> Copiado!';
                buttonEl.style.background = 'var(--cor-sucesso)';
                setTimeout(() => {
                    buttonEl.innerHTML = originalText;
                    buttonEl.style.background = ''; // Reseta o background, se aplicável
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


function mudarLoteria(novaLoteria) {
    loteriaAtual = novaLoteria;
    document.getElementById('loteria-select').value = novaLoteria; // Garante que o seletor principal está sempre certo
    const config = lotteryConfig[loteriaAtual];
    const displayLoteria = document.getElementById('loteria-selecionada');
    displayLoteria.textContent = config.nome;
    displayLoteria.style.opacity = 1;

    // Sincroniza o seletor de resultados com o seletor principal
    const seletorResultados = document.getElementById('loteria-select-resultados');
    if (seletorResultados) {
        seletorResultados.value = novaLoteria;
    }

    document.getElementById('nome-loteria-resultados').textContent = config.nome;
    
    atualizarOpcoesDezenas();
    atualizarOpcoesQuantidade();
    handleEstrategiaChange();
    
    document.getElementById('area-resultados').innerHTML = '';
    document.getElementById('area-estatisticas').style.display = 'none';
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
    document.getElementById('nome-loteria-resultados').textContent = config.nome;
    carregarUltimosResultados(novaLoteria);
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
    } else {
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

async function exibirEstatisticas() {
    const botao = document.querySelector('#estatisticas .botao-gerar');
        if (isRequestInProgress || botao.disabled) return;
    
    const areaStats = document.getElementById('area-estatisticas');
    isRequestInProgress = true;
    botao.disabled = true;
    botao.innerHTML = '<div class="spinner" style="width: 25px; height: 25px; margin: 0 auto;"></div>';
    
    try {
        const response = await fetch(`/get-stats?loteria=${loteriaAtual}`);
        if (!response.ok) throw new Error('Falha ao buscar dados do servidor.');
        const data = await response.json();
        if (data.error || !data.frequencia || !data.stats_primos || !data.stats_pares) throw new Error(data.error || 'Os dados recebidos são inválidos.');

        const nomeLoteria = lotteryConfig[loteriaAtual].nome;
        document.getElementById('ultimo-concurso-info').innerHTML = `Análise da ${nomeLoteria} baseada até o concurso ${data.ultimo_concurso}`;
        areaStats.style.display = 'block';

        [graficoMaisSorteados, graficoMenosSorteados, graficoPrimos, graficoParesImpares].forEach(g => { if(g) g.destroy(); });

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

        const maisSorteados = [...data.frequencia].sort((a, b) => b.frequencia - a.frequencia).slice(0, 10);
        graficoMaisSorteados = new Chart(document.getElementById('grafico-mais-sorteados').getContext('2d'), { type: 'bar', data: { labels: maisSorteados.map(i => `Nº ${i.numero}`), datasets: [{ label: 'Vezes Sorteado', data: maisSorteados.map(i => i.frequencia), backgroundColor: '#FFD700' }] }, options: chartOptions });
        
        const menosSorteados = [...data.frequencia].sort((a, b) => a.frequencia - b.frequencia).slice(0, 10);
        graficoMenosSorteados = new Chart(document.getElementById('grafico-menos-sorteados').getContext('2d'), { type: 'bar', data: { labels: menosSorteados.map(i => `Nº ${i.numero}`), datasets: [{ label: 'Vezes Sorteado', data: menosSorteados.map(i => i.frequencia), backgroundColor: '#90CAF9' }] }, options: chartOptions });
        
        const labelsPrimos = Object.keys(data.stats_primos).sort((a,b) => parseInt(a)-parseInt(b)).map(k => `${k} Primos`);
        const dataPrimos = Object.keys(data.stats_primos).sort((a,b) => parseInt(a)-parseInt(b)).map(k => data.stats_primos[k]);
        graficoPrimos = new Chart(document.getElementById('grafico-primos').getContext('2d'), { type: 'bar', data: { labels: labelsPrimos, datasets: [{ label: 'Sorteios', data: dataPrimos, backgroundColor: '#81C784' }] }, options: chartOptions });
        
        const numBolas = lotteryConfig[loteriaAtual].num_bolas;
        const labelsPares = Object.keys(data.stats_pares).sort((a,b) => parseInt(a)-parseInt(b)).map(k => `${k} Pares / ${numBolas - parseInt(k)} Ímpares`);
        const dataPares = Object.keys(data.stats_pares).sort((a,b) => parseInt(a)-parseInt(b)).map(k => data.stats_pares[k]);
        graficoParesImpares = new Chart(document.getElementById('grafico-pares-impares').getContext('2d'), { type: 'bar', data: { labels: labelsPares, datasets: [{ label: 'Sorteios', data: dataPares, backgroundColor: '#FF8A65' }] }, options: chartOptions });
        
        botao.style.display = 'none';

    } catch (error) {
        areaStats.innerHTML = `<p style="color: #ff8a80;">${error.message}</p>`;
        areaStats.style.display = 'block';
        botao.innerHTML = 'Estatísticas';
        botao.disabled = false;
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

            html += `
                <div class="resultado-item">
                    <div class="resultado-header">
                        <span class="resultado-concurso">Concurso ${res.concurso}</span>
                        <span class="resultado-data">${res.data}</span>
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

// ======================================
//             SEÇÃO BLOG
// ======================================

let artigosVisiveis = 5;
const totalArtigos = 9; // Pode ser dinamicamente obtido se os artigos forem carregados via API

function carregarMaisArtigos() {
    const artigos = document.querySelectorAll('.artigo-blog:not(.visivel)');
    const proximosArtigos = Math.min(4, artigos.length);
    
    for (let i = 0; i < proximosArtigos; i++) {
        artigos[i].classList.add('visivel');
        artigosVisiveis++;
    }
    
    // Atualiza contador
    document.getElementById('contador-artigos').textContent = 
        `Mostrando ${artigosVisiveis} de ${totalArtigos} artigos`;
    
    // Esconde o botão se não há mais artigos
    if (artigosVisiveis >= totalArtigos) {
        document.querySelector('.carregar-mais').style.display = 'none';
        document.querySelector('.carregar-mais-container p').innerHTML = 
            '<span style="color: var(--cor-sucesso);">✓ Todos os artigos carregados!</span>';
    }
    
    // Scroll suave para o primeiro novo artigo
    if (artigos.length > 0) {
        artigos[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

function toggleArtigo(artigoId) {
    const conteudo = document.getElementById(artigoId);
    const artigoPai = conteudo.closest('.artigo-blog');
    const resumo = artigoPai.querySelector('.artigo-resumo');
    const icone = artigoPai.querySelector('.fa-chevron-down, .fa-chevron-up');

    if (conteudo.classList.contains('artigo-expandido')) {
        conteudo.classList.remove('artigo-expandido');
        resumo.style.display = 'block';
        icone.classList.remove('fa-chevron-up');
        icone.classList.add('fa-chevron-down');
    } else {
        conteudo.classList.add('artigo-expandido');
        resumo.style.display = 'none';
        icone.classList.remove('fa-chevron-down');
        icone.classList.add('fa-chevron-up');
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
    // Instagram não permite compartilhamento direto via URL para posts.
    // O mais próximo seria direcionar para o perfil ou para o site.
    window.open('https://www.instagram.com/sorteanalisadaoficial/', '_blank'); // Exemplo: ir para o perfil
}

function compartilharTikTok() {
    // TikTok também não permite compartilhamento direto via URL para vídeos.
    // O mais próximo seria direcionar para o perfil ou para a página de upload.
    window.open('https://www.tiktok.com/upload', '_blank'); // Exemplo: ir para a página de upload
}

function copiarLink(url, event) { // Adicionado 'event' para pegar o botão
    navigator.clipboard.writeText(url).then(() => {
        const btn = event.target.closest('.share-btn');
        if (btn) { // Garante que o botão existe
            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fa-solid fa-check"></i> Copiado!';
            btn.style.background = 'var(--cor-sucesso)';
            
            setTimeout(() => {
                btn.innerHTML = originalText;
                btn.style.background = '#6c757d'; // Volta à cor original do "Copiar Link"
            }, 2000);
        }
    }).catch(() => {
        alert('Link copiado: ' + url);
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

        // Atribui eventos aos seletores
        seletorPrincipal.addEventListener('change', () => mudarLoteria(seletorPrincipal.value));
        const seletorResultados = document.getElementById('loteria-select-resultados');
        if (seletorResultados) {
            seletorResultados.addEventListener('change', () => mudarLoteriaResultados(seletorResultados.value));
        }
        document.getElementById('estrategia-select')?.addEventListener('change', handleEstrategiaChange);
        document.getElementById('botao-gerar-principal')?.addEventListener('click', gerarPalpites);
        document.querySelector('#estatisticas .botao-gerar')?.addEventListener('click', exibirEstatisticas);
    }
    
    // --- BLOG ---
    const contadorArtigos = document.getElementById('contador-artigos');
    if (contadorArtigos) {
        contadorArtigos.textContent = `Mostrando ${artigosVisiveis} de ${totalArtigos} artigos`;
        document.querySelector('.carregar-mais')?.addEventListener('click', carregarMaisArtigos);

        // Garante que os 5 primeiros artigos estejam visíveis na carga inicial
        document.querySelectorAll('.artigo-blog').forEach((artigo, index) => {
            if (index < artigosVisiveis) {
                artigo.classList.add('visivel');
            }
        });
    }

    // Adiciona listener para todos os botões de copiar globais (se não forem parte de .jogo)
    document.querySelectorAll('.share-btn.copy-link').forEach(btn => {
        btn.addEventListener('click', (e) => copiarLink(btn.dataset.url, e));
    });
});