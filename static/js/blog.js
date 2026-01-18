// ==============================
//      VARIÁVEIS DO BLOG
// ==============================
let artigosVisiveis = 5;
const totalArtigos = 11;

// ==============================
//      INICIALIZAÇÃO DO BLOG
// ==============================
document.addEventListener('DOMContentLoaded', function() {
    console.log('Blog.js carregado - Inicializando...');
    
    // Inicializar estado dos artigos
    inicializarArtigos();
    
    // Configurar event listeners
    configurarEventListenersBlog();
    
    // Atualizar contador
    atualizarContadorArtigos();
});

// ==============================
//      INICIALIZAÇÃO DOS ARTIGOS
// ==============================
function inicializarArtigos() {
    const artigos = getElements(".artigo-blog");
    console.log(`Inicializando ${artigos.length} artigos`);
    
    artigos.forEach((artigo, index) => {
        // Mostrar apenas os primeiros artigos
        if (index < artigosVisiveis) {
            artigo.classList.add("visivel");
        } else {
            artigo.classList.remove("visivel");
        }
        
        // Inicializar conteúdo (fechado)
        const conteudo = artigo.querySelector('.artigo-conteudo');
        const resumo = artigo.querySelector('.artigo-resumo');
        const icon = artigo.querySelector('.artigo-blog-header i');
        
        if (conteudo) {
            conteudo.classList.remove('artigo-expandido');
        }
        if (resumo) {
            resumo.style.display = 'block';
        }
        if (icon) {
            icon.className = 'fa-solid fa-chevron-down';
        }
    });
}

// ==============================
//      GERENCIAMENTO DE ARTIGOS
// ==============================
function carregarMaisArtigos() {
    console.log('Carregando mais artigos...');
    
    const artigos = getElements(".artigo-blog");
    const artigosOcultos = Array.from(artigos).filter(artigo => !artigo.classList.contains('visivel'));
    const quantidadeCarregar = Math.min(6, artigosOcultos.length);
    
    console.log(`Artigos ocultos: ${artigosOcultos.length}, Carregando: ${quantidadeCarregar}`);
    
    for (let i = 0; i < quantidadeCarregar; i++) {
        artigosOcultos[i].classList.add("visivel");
        artigosVisiveis++;
        console.log(`Artigo ${i + 1} tornado visível`);
    }
    
    atualizarContadorArtigos();
    
    // Scroll para o primeiro artigo carregado
    if (artigosOcultos.length > 0 && quantidadeCarregar > 0) {
        setTimeout(() => {
            artigosOcultos[0].scrollIntoView({ behavior: "smooth", block: "start" });
        }, 300);
    }
}

function atualizarContadorArtigos() {
    const contadorArtigos = getElement("contador-artigos");
    if (contadorArtigos) {
        contadorArtigos.textContent = `Mostrando ${artigosVisiveis} de ${totalArtigos} artigos`;
        console.log(`Contador atualizado: ${artigosVisiveis} de ${totalArtigos}`);
    }
    
    const botaoCarregarMais = document.querySelector(".carregar-mais");
    const mensagemCarregar = document.querySelector(".carregar-mais-container p");
    
    if (artigosVisiveis >= totalArtigos) {
        if (botaoCarregarMais) {
            botaoCarregarMais.style.display = 'none';
            console.log('Botão carregar mais ocultado - todos os artigos visíveis');
        }
        if (mensagemCarregar) {
            mensagemCarregar.innerHTML = '<span style="color: var(--cor-sucesso);">✓ Todos os artigos carregados!</span>';
        }
    } else {
        if (botaoCarregarMais) {
            botaoCarregarMais.style.display = 'block'; // Garantir que está visível
        }
    }
}

function toggleArtigo(artigoId) {
    console.log('Toggle artigo:', artigoId);
    
    const artigoConteudo = getElement(artigoId);
    if (!artigoConteudo) {
        console.log('Conteúdo do artigo não encontrado:', artigoId);
        return;
    }
    
    const artigoContainer = artigoConteudo.closest('.artigo-blog');
    const resumo = artigoContainer.querySelector('.artigo-resumo');
    const icon = artigoContainer.querySelector('.artigo-blog-header i');
    
    const isExpandido = artigoConteudo.classList.contains('artigo-expandido');
    
    console.log('Artigo está expandido?:', isExpandido);
    
    // Alternar classes CSS
    if (isExpandido) {
        // Fechar artigo
        artigoConteudo.classList.remove('artigo-expandido');
        if (resumo) resumo.style.display = 'block';
        if (icon) icon.className = 'fa-solid fa-chevron-down';
    } else {
        // Abrir artigo
        artigoConteudo.classList.add('artigo-expandido');
        if (resumo) resumo.style.display = 'none';
        if (icon) icon.className = 'fa-solid fa-chevron-up';
        
        // Scroll suave para o artigo
        setTimeout(() => {
            artigoContainer.scrollIntoView({ behavior: "smooth", block: "start" });
        }, 300);
    }
}

// ==============================
//      CONFIGURAÇÃO DE EVENT LISTENERS DO BLOG
// ==============================
function configurarEventListenersBlog() {
    console.log('Configurando event listeners do blog...');
    
    // Botão carregar mais artigos
    const botaoCarregarMais = document.querySelector(".carregar-mais");
    if (botaoCarregarMais) {
        botaoCarregarMais.addEventListener("click", carregarMaisArtigos);
        console.log('Event listener adicionado ao botão carregar mais');
    } else {
        console.log('Botão carregar mais não encontrado');
    }
    
    // Configurar toggle dos artigos
    const artigos = getElements(".artigo-blog");
    console.log(`Encontrados ${artigos.length} artigos`);
    
    artigos.forEach(artigo => {
        // Inicializar estado dos artigos (todos fechados)
        const conteudo = artigo.querySelector('.artigo-conteudo');
        const resumo = artigo.querySelector('.artigo-resumo');
        const icon = artigo.querySelector('.artigo-blog-header i');
        
        if (conteudo) {
            conteudo.classList.remove('artigo-expandido'); // Garantir que começa fechado
        }
        if (resumo) {
            resumo.style.display = 'block'; // Resumo visível
        }
        if (icon) {
            icon.className = 'fa-solid fa-chevron-down'; // Ícone para baixo
        }
        
        // Adicionar event listener para toggle
        artigo.addEventListener("click", function(e) {
            console.log('Clicou no artigo');
            
            // Evitar que o toggle aconteça quando clicar em links de compartilhamento ou outros elementos
            if (e.target.tagName === 'A' || e.target.closest('a') || e.target.closest('.share-container')) {
                console.log('Clicou em link/compartilhamento - ignorando toggle');
                return;
            }
            
            const artigoConteudo = this.querySelector('.artigo-conteudo');
            if (artigoConteudo && artigoConteudo.id) {
                console.log('Toggle no artigo:', artigoConteudo.id);
                toggleArtigo(artigoConteudo.id);
            } else {
                console.log('Conteúdo do artigo não encontrado ou sem ID');
            }
        });
    });
}