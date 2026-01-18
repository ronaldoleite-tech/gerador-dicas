// ==============================
//          UTILITÁRIOS GLOBAIS
// ==============================
function getElement(id) { return document.getElementById(id); }
function getElements(selector) { return document.querySelectorAll(selector); }

// ==============================
//      SISTEMA DE COMPARTILHAMENTO
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
    copy: (url, botao) => {
        navigator.clipboard.writeText(url).then(() => {
            if (botao) {
                const originalHtml = botao.innerHTML;
                botao.innerHTML = '<i class="fa-solid fa-check"></i> Copiado!';
                botao.style.background = "var(--cor-sucesso)";
                setTimeout(() => {
                    botao.innerHTML = originalHtml;
                    botao.style.background = "";
                }, 2000);
            }
        });
    }
};

// Atalhos globais para as tags onclick do HTML
window.compartilharWhatsApp = (url) => compartilhamento.whatsapp(document.title, url);
window.compartilharFacebook = (url) => compartilhamento.facebook(url);
window.compartilharTwitter = (url) => compartilhamento.twitter(document.title, url);
window.copiarLink = (url, event) => {
    const btn = event?.target?.closest(".share-btn") || event?.target;
    compartilhamento.copy(url, btn);
};

// ==============================
//         UI E NAVEGAÇÃO
// ==============================
function configurarDropdowns() {
    const dropdowns = document.querySelectorAll('.dropdown');
    dropdowns.forEach(dropdown => {
        const toggle = dropdown.querySelector('a:first-child');
        toggle.addEventListener('click', (e) => {
            e.preventDefault();
            dropdown.classList.toggle('active');
        });
    });
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.dropdown')) {
            dropdowns.forEach(d => d.classList.remove('active'));
        }
    });
}

function carregarFooter() {
    const footerElement = getElement("footer");
    if (footerElement) {
        fetch("/static/partials/footer.html")
            .then(r => r.text())
            .then(html => { footerElement.innerHTML = html; })
            .catch(e => console.error("Erro footer:", e));
    }
}

document.addEventListener("DOMContentLoaded", () => {
    carregarFooter();
    configurarDropdowns();
});