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

fetch("/static/partials/footer.html")
    .then(response => response.text())
    .then(data => {
        document.getElementById("footer").innerHTML = data;
    })
    .catch(err => console.error("Erro ao carregar rodapé:", err));






