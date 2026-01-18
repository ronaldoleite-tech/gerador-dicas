// ==============================
//      CONFIGURAÇÃO E ESTADO
// ==============================
const LOCAL_CONFIG = {
    'megasena': { nome: 'Mega-Sena', min_num: 1, max_num: 60, min_dezenas: 6, max_dezenas: 20, default_dezenas: 6, num_bolas_sorteadas: 6 },
    'quina': { nome: 'Quina', min_num: 1, max_num: 80, min_dezenas: 5, max_dezenas: 15, default_dezenas: 5, num_bolas_sorteadas: 5 },
    'lotofacil': { nome: 'Lotofácil', min_num: 1, max_num: 25, min_dezenas: 15, max_dezenas: 20, default_dezenas: 15, num_bolas_sorteadas: 15 },
    'diadesorte': { nome: 'Dia de Sorte', min_num: 1, max_num: 31, min_dezenas: 7, max_dezenas: 15, default_dezenas: 7, num_bolas_sorteadas: 7 },
    'duplasena': { nome: 'Dupla Sena', min_num: 1, max_num: 50, min_dezenas: 6, max_dezenas: 15, default_dezenas: 6, num_bolas_sorteadas: 6 },
    'lotomania': { nome: 'Lotomania', min_num: 1, max_num: 100, min_dezenas: 50, max_dezenas: 50, default_dezenas: 50, num_bolas_sorteadas: 20 },
    'timemania': { nome: 'Timemania', min_num: 1, max_num: 80, min_dezenas: 10, max_dezenas: 10, default_dezenas: 10, num_bolas_sorteadas: 7 },
    'supersete': { nome: 'Super Sete', min_num: 0, max_num: 9, min_dezenas: 7, max_dezenas: 7, default_dezenas: 7, num_bolas_sorteadas: 7 },
    'maismilionaria': { nome: '+Milionária', min_num: 1, max_num: 50, min_dezenas: 6, max_dezenas: 12, default_dezenas: 6, num_bolas_sorteadas: 6 }
};

let loteriaAtual = "megasena";
let numerosSelecionadosFechamento = new Set();
const meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];

// ==============================
//      INICIALIZAÇÃO
// ==============================
document.addEventListener('DOMContentLoaded', () => {
    // 1. Inicializa Gerador
    if (document.getElementById("loteria-select")) {
        const sel = document.getElementById("loteria-select");
        sel.addEventListener("change", (e) => mudarLoteria(e.target.value));
        document.getElementById("botao-gerar-principal").addEventListener("click", gerarPalpites);
        mudarLoteria("megasena");
    }

    // 2. Inicializa Organizador
    if (document.getElementById('loteria-fechamento')) {
        const selFechamento = document.getElementById('loteria-fechamento');
        selFechamento.addEventListener('change', () => {
            numerosSelecionadosFechamento.clear();
            gerarGridNumeros();
            atualizarContadorFechamento();
        });
        document.getElementById("btn-gerar-fechamento").addEventListener("click", gerarFechamento);
        document.getElementById("btn-limpar-fechamento").addEventListener("click", () => {
            numerosSelecionadosFechamento.clear();
            gerarGridNumeros();
            atualizarContadorFechamento();
            document.getElementById('resultado-fechamento').style.display = 'none';
        });
        gerarGridNumeros();
        atualizarContadorFechamento();
    }
});

// ==============================
//      LÓGICA DO GERADOR
// ==============================
function mudarLoteria(key) {
    loteriaAtual = key;
    const config = LOCAL_CONFIG[key];
    document.getElementById("loteria-selecionada").textContent = config.nome;
    
    const dezSel = document.getElementById("dezenas-select");
    dezSel.innerHTML = "";
    for (let i = config.min_dezenas; i <= config.max_dezenas; i++) {
        const opt = document.createElement("option");
        opt.value = i;
        opt.textContent = `${i} Dezenas`;
        if (i === config.default_dezenas) opt.selected = true;
        dezSel.appendChild(opt);
    }

    const qtdSel = document.getElementById("quantidade-select");
    qtdSel.innerHTML = "";
    for (let i = 1; i <= 10; i++) {
        const opt = document.createElement("option");
        opt.value = i;
        opt.textContent = `${i} Jogo${i > 1 ? 's' : ''}`;
        qtdSel.appendChild(opt);
    }
}

async function gerarPalpites() {
    const btn = document.getElementById("botao-gerar-principal");
    const area = document.getElementById("area-resultados");
    const dezenas = document.getElementById("dezenas-select").value;
    const qtd = document.getElementById("quantidade-select").value;
    const ancora = document.getElementById("numeros-ancora").value;

    btn.disabled = true;
    area.innerHTML = '<div class="spinner"></div>';

    try {
        const resp = await fetch(`/get-games/${qtd}?loteria=${loteriaAtual}&dezenas=${dezenas}&ancora=${ancora}`);
        const jogos = await resp.json();

        area.innerHTML = "<h2>Boa sorte!</h2>";
        jogos.forEach(jogo => {
            const div = document.createElement("div");
            div.className = "jogo";
            div.innerHTML = `
                <div class="numeros-container">
                    ${jogo.split(" ").map(n => `<span class="numero">${n}</span>`).join("")}
                    ${loteriaAtual === 'diadesorte' ? ` | Mês: <strong>${meses[Math.floor(Math.random()*12)]}</strong>` : ''}
                </div>
                <button class="botao-copiar" onclick="window.compartilhamento.copy('${jogo}', this)">
                    <i class="fa-regular fa-copy"></i>
                </button>
            `;
            area.appendChild(div);
        });
    } catch (e) {
        area.innerHTML = "<p>Erro ao gerar jogos.</p>";
    } finally {
        btn.disabled = false;
    }
}

// ==============================
//      LÓGICA DO ORGANIZADOR
// ==============================
function gerarGridNumeros() {
    const grid = document.getElementById('grid-numeros-fechamento');
    const lot = document.getElementById('loteria-fechamento').value;
    const config = LOCAL_CONFIG[lot];
    grid.innerHTML = "";
    for (let i = config.min_num; i <= config.max_num; i++) {
        const btn = document.createElement('button');
        btn.className = 'numero-botao';
        btn.textContent = String(i).padStart(2, '0');
        if (numerosSelecionadosFechamento.has(i)) btn.classList.add('selecionado');
        btn.onclick = () => {
            if (numerosSelecionadosFechamento.has(i)) {
                numerosSelecionadosFechamento.delete(i);
                btn.classList.remove('selecionado');
            } else if (numerosSelecionadosFechamento.size < config.max_dezenas) {
                numerosSelecionadosFechamento.add(i);
                btn.classList.add('selecionado');
            }
            atualizarContadorFechamento();
        };
        grid.appendChild(btn);
    }
}

function atualizarContadorFechamento() {
    const lot = document.getElementById('loteria-fechamento').value;
    const config = LOCAL_CONFIG[lot];
    const min = config.num_bolas_sorteadas + 1;
    document.getElementById('contador-fechamento').textContent = 
        `Selecionados: ${numerosSelecionadosFechamento.size} | Mínimo para organizar: ${min}`;
    document.getElementById('btn-gerar-fechamento').disabled = numerosSelecionadosFechamento.size < min;
}

async function gerarFechamento() {
    const loading = document.getElementById('loading-fechamento');
    const resultadoArea = document.getElementById('resultado-fechamento');
    const lot = document.getElementById('loteria-fechamento').value;
    const qtdJogos = parseInt(document.getElementById('quantidade-jogos').value);
    
    loading.style.display = 'flex';
    resultadoArea.style.display = 'none';

    await new Promise(r => setTimeout(r, 600)); // Simula processamento

    try {
        const selecionados = Array.from(numerosSelecionadosFechamento);
        const dezenasPorJogo = LOCAL_CONFIG[lot].num_bolas_sorteadas;
        
        const jogos = realizarDistribuicao(selecionados, dezenasPorJogo, qtdJogos);
        exibirResultadoOrganizador(jogos, selecionados, lot);
    } catch (e) {
        alert("Erro ao organizar jogos.");
    } finally {
        loading.style.display = 'none';
    }
}

function realizarDistribuicao(selecionados, dezenasPorJogo, totalJogos) {
    let jogos = [];
    let freq = {};
    selecionados.forEach(n => freq[n] = 0);

    for (let i = 0; i < totalJogos; i++) {
        let pool = [...selecionados].sort((a, b) => (freq[a] + Math.random()) - (freq[b] + Math.random()));
        let jogo = pool.slice(0, dezenasPorJogo).sort((a, b) => a - b);
        jogos.push(jogo);
        jogo.forEach(n => freq[n]++);
    }
    return jogos;
}

function exibirResultadoOrganizador(jogos, selecionados, lot) {
    const area = document.getElementById('resultado-fechamento');
    let html = `
        <div class="fechamento-resultado">
            <h3><i class="fas fa-check-circle"></i> Jogos Organizados</h3>
            <p>Seus números: ${selecionados.sort((a,b)=>a-b).join(', ')}</p>
            <div class="jogos-container">
    `;

    jogos.forEach((jogo, i) => {
        const jogoStr = jogo.map(n => String(n).padStart(2, '0')).join(' ');
        html += `
            <div class="jogo-fechamento">
                <strong>Jogo ${i + 1}</strong>
                <div class="jogo-numeros">${jogo.map(n => `<span class="numero-jogo">${String(n).padStart(2, '0')}</span>`).join('')}</div>
                <button class="btn-copiar-jogo" onclick="window.compartilhamento.copy('${jogoStr}', this)">
                    <i class="fa-regular fa-copy"></i>
                </button>
            </div>
        `;
    });

    html += `</div><button class="botao-gerar" onclick="baixarCSVOrganizador('${lot}')"><i class="fas fa-file-csv"></i> Baixar CSV</button></div>`;
    area.innerHTML = html;
    area.style.display = 'block';
    area.scrollIntoView({ behavior: 'smooth' });
}

window.baixarCSVOrganizador = (lot) => {
    let csv = "Jogo;Dezenas\n";
    document.querySelectorAll('.jogo-fechamento').forEach((node, i) => {
        const nums = Array.from(node.querySelectorAll('.numero-jogo')).map(s => s.textContent).join(' ');
        csv += `${i+1};${nums}\n`;
    });
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `jogos_${lot}.csv`;
    link.click();
};