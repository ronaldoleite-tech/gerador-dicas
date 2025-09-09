
        // ============== CONTROLE DE PAGINAÇÃO ============== 
        let artigosVisiveis = 5;
        const totalArtigos = 9;

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

        // ============== TOGGLE DE ARTIGOS (VERSÃO MELHORADA) ============== 
        function toggleArtigo(artigoId) {
            const conteudo = document.getElementById(artigoId);
            // Encontre o resumo dentro do mesmo "pai" que o conteúdo
            const artigoPai = conteudo.closest('.artigo-blog');
            const resumo = artigoPai.querySelector('.artigo-resumo');
            const icone = artigoPai.querySelector('.fa-chevron-down, .fa-chevron-up');

            // Se o artigo está expandido (estado atual)
            if (conteudo.classList.contains('artigo-expandido')) {
                conteudo.classList.remove('artigo-expandido');
                resumo.style.display = 'block';
                icone.classList.remove('fa-chevron-up');
                icone.classList.add('fa-chevron-down');
            } 
            // Se o artigo está recolhido (estado atual)
            else {
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

        
       function compartilharFacebook() {
            const urlDoSite = "https://sorteanalisada.com.br/blog/";
            window.open(`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(urlDoSite)}`, '_blank');
        }

        function compartilharTwitter(texto, url) {
            const tweet = encodeURIComponent(`${texto} ${url}`);
            window.open(`https://twitter.com/intent/tweet?text=${tweet}`, '_blank');
        }

        // Nova função para o Threads
        function compartilharThreads(texto, url) {
            const thread = encodeURIComponent(`${texto} ${url}`);
            window.open(`https://www.threads.net/intent/post?text=${thread}`, '_blank');
        }

        function compartilharInstagram() {
            window.open('https://www.instagram.com/', '_blank');
        }

        function compartilharTikTok() {
            window.open('https://www.tiktok.com/upload', '_blank');
        }

        function copiarLink(url) {
            navigator.clipboard.writeText(url).then(() => {
                // Feedback visual temporário
                const btn = event.target.closest('.share-btn');
                const originalText = btn.innerHTML;
                btn.innerHTML = '<i class="fa-solid fa-check"></i> Copiado!';
                btn.style.background = 'var(--cor-sucesso)';
                
                setTimeout(() => {
                    btn.innerHTML = originalText;
                    btn.style.background = '#6c757d';
                }, 2000);
            }).catch(() => {
                alert('Link copiado: ' + url);
            });
        }

        // ============== INICIALIZAÇÃO ============== 
        document.addEventListener('DOMContentLoaded', function() {
            // Atualiza contador inicial
            document.getElementById('contador-artigos').textContent = 
                `Mostrando ${artigosVisiveis} de ${totalArtigos} artigos`;
        });
   