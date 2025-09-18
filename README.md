
# Selecionilda

Selecionilda é uma ferramenta de entrevistas de emprego simuladas utilizando Inteligência Artificial via PollinationsAI. Desenvolvido em Python, o projeto gera um relatório em PDF com **avaliação detalhada do candidato**, baseada nas perguntas feitas durante a entrevista.

Principais tecnologias: Python 3.7+, asyncio, requests, curses, reportlab, PollinationsAI.

## Como usar

1.  **Clonar o projeto**
    ```bash
    git clone https://github.com/funandmemes/selecionilda.git 
    cd selecionilda
    ```
2.  **Instalar dependências**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Rodar a entrevista**
    ```bash
    python entrevista.py
    ```
4.  **Trocar o modelo de IA**
    ```bash
    python entrevista.py --config
    ```

Um menu interativo permitirá selecionar o modelo desejado. O modelo será salvo para uso nas próximas entrevistas.

## Pontos positivos

-   Entrevista personalizada baseada na descrição da vaga.
    
-   Perguntas técnicas e comportamentais geradas automaticamente.
    
-   PDF final contém **avaliação detalhada do candidato**.
    
-   Suporte a múltiplos modelos de IA via PollinationsAI.
    
-   Totalmente em Python, fácil de executar em Windows ou Linux.
