________________________________________
🍀 Sorte Analisada
Seu gerador inteligente de palpites para as Loterias Brasileiras. Este projeto utiliza Python, Flask e análise de dados históricos para oferecer sugestões de jogos, indo além da simples aleatoriedade.
Acesse a aplicação em: sorteanalisada.com.br
<!-- Sugestão: Tire um print bonito da sua aplicação e substitua este link -->
🎯 Sobre o Projeto
O Sorte Analisada é uma aplicação web completa que oferece palpites para as principais loterias do Brasil (Mega-Sena, Quina, Lotofácil e Dia de Sorte). A principal diferença é a capacidade de gerar números com base em diferentes estratégias, incluindo a frequência histórica de todos os resultados, simulações de Monte Carlo e a personalização com o "número da sorte" do usuário.
Tecnologias utilizadas:
•	Backend: Python com Flask
•	Frontend: HTML5, CSS3 e JavaScript (vanilla)
•	Banco de Dados: PostgreSQL
•	Hospedagem: Render
✨ Funcionalidades Principais
•	Suporte a Múltiplas Loterias: Gere jogos para Mega-Sena, Quina, Lotofácil e Dia de Sorte.
•	Filtro Inteligente: Opte por gerar jogos com base na frequência histórica dos números, dando mais peso aos que mais saíram.
•	Geração 100% Aleatória: A clássica "surpresinha", para quem acredita que a sorte não tem memória.
•	Simulação de Monte Carlo: Uma "Dica Especial" que usa uma análise de probabilidade avançada para um palpite único e sofisticado.
•	Jogo Âncora: Insira seu "número da sorte" e deixe o sistema completar o restante do jogo de forma inteligente.
•	Análise Estatística: Visualize gráficos com as dezenas mais e menos sorteadas, distribuição de pares/ímpares e números primos.
🚀 Como Executar o Projeto Localmente
Siga os passos abaixo para ter uma cópia do projeto rodando na sua máquina.
Pré-requisitos
•	Python 3.x
•	Git
•	Uma instância de banco de dados PostgreSQL
Instalação
1.	Clone o repositório:
codeBash
git clone https://github.com/ronaldo-leite-tech/SorteAnalisada.git # Substitua pela URL correta do seu repo
cd SorteAnalisada
2.	(Opcional, mas recomendado) Crie um ambiente virtual:
codeBash
python -m venv venv
# No Windows:
venv\Scripts\activate
# No Linux/Mac:
source venv/bin/activate
3.	Instale as dependências:
(Observação: Sugiro renomear seu arquivo requisitos.txt para requirements.txt, que é o padrão da comunidade Python)
codeBash
pip install -r requirements.txt
4.	Configure as variáveis de ambiente:
o	Crie um arquivo chamado .env na raiz do projeto.
o	Dentro dele, adicione a URL de conexão do seu banco de dados PostgreSQL:
codeCode
DATABASE_URL="postgres://SEU_USUARIO:SUA_SENHA@SEU_HOST/SEU_BANCO"
5.	Popule o banco de dados:
o	Certifique-se de que os arquivos .txt com os resultados dos sorteios (sorteadosmegasena.txt, etc.) estão na raiz do projeto.
o	Execute o script de importação:
codeBash
python importador.py
6.	Execute a aplicação Flask:
codeBash
python backend.py
Acesse http://127.0.0.1:10000 no seu navegador.
⚠️ Aviso Legal
Importante: Este é um projeto para fins de estudo e entretenimento. A geração de números não garante nenhum ganho na loteria. As probabilidades de acerto permanecem as mesmas para qualquer combinação. Jogue com responsabilidade.
Este projeto não possui qualquer vínculo com a Caixa Econômica Federal ou outra entidade lotérica.
👏 Como Contribuir
Contribuições são super bem-vindas! Sinta-se à vontade para:
•	Relatar bugs
•	Sugerir melhorias e novas funcionalidades
•	Enviar pull requests
📄 Licença
Este projeto está sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.
