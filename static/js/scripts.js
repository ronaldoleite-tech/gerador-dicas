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

fetch("/static/rodape/footer.html")
    .then(response => response.text())
    .then(data => {
        document.getElementById("footer").innerHTML = data;
    })
    .catch(err => console.error("Erro ao carregar rodapé:", err));



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