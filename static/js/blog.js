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
