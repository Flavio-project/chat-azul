from datetime import datetime, timedelta
import re
import unicodedata
import os

def normalizar(texto):
    if not texto: return ""
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII').lower().strip()

def carregar_categorias(caminho_arquivo):
    categorias = []
    if not os.path.exists(caminho_arquivo):
        return categorias
    with open(caminho_arquivo, encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if linha and not linha.upper().startswith("DRE:"):
                categorias.append(linha)
    return categorias

class SmartAnalyzer:
    def __init__(self, oauth2_instance, caminho_categorias="CATEGORIAS - CONTA AZUL.txt"):
        self.oauth2 = oauth2_instance
        self.categorias = carregar_categorias(caminho_categorias)

    def interpretar_periodo(self, pergunta):
        hoje = datetime.now()
        pergunta_norm = normalizar(pergunta)
        
        if "mes passado" in pergunta_norm:
            mes = hoje.month - 1 or 12
            ano = hoje.year if hoje.month > 1 else hoje.year - 1
            data_de = datetime(ano, mes, 1)
            data_ate = datetime(hoje.year, hoje.month, 1) - timedelta(days=1)
        elif "este mes" in pergunta_norm or "esse mes" in pergunta_norm:
            data_de = datetime(hoje.year, hoje.month, 1)
            data_ate = hoje
        elif "este ano" in pergunta_norm or "esse ano" in pergunta_norm:
            data_de = datetime(hoje.year, 1, 1)
            data_ate = hoje
        else: # Padrão: Últimos 30 dias se nenhum período for especificado
            data_de = hoje - timedelta(days=30)
            data_ate = hoje
            
        return data_de.strftime("%Y-%m-%d"), data_ate.strftime("%Y-%m-%d")

    def analisar_pergunta(self, pergunta):
        pergunta_norm = normalizar(pergunta)
        data_de, data_ate = self.interpretar_periodo(pergunta)

        categoria_encontrada = None
        candidatas = []
        for cat in self.categorias:
            cat_norm = normalizar(cat)
            palavras_cat = cat_norm.split()
            if all(palavra in pergunta_norm for palavra in palavras_cat):
                candidatas.append((cat, len(cat_norm)))
        if candidatas:
            categoria_encontrada = sorted(candidatas, key=lambda x: x[1], reverse=True)[0][0]

        # Extrai a descrição (o que sobra da pergunta)
        descricao = pergunta
        termos_para_remover = [categoria_encontrada, "quanto gastei de", "quanto gastei com", "gastos com", "custo de", "despesas com", "este ano", "esse ano", "este mes", "esse mes", "mes passado", "?"]
        if descricao:
            for termo in termos_para_remover:
                if termo: descricao = descricao.replace(termo, "").strip()
        
        return {
            "data_de": data_de,
            "data_ate": data_ate,
            "categoria_nome": categoria_encontrada,
            "descricao_texto": descricao or None
        }

    def formatar_resposta(self, dados, analise):
        if not dados or not dados.get("itens"):
            return "❌ Nenhum gasto encontrado para os filtros informados."
        
        dados_filtrados = dados["itens"]
        total_gasto = sum(float(item.get("total", 0)) for item in dados_filtrados)
        periodo = analise["data_de"] + " até " + analise["data_ate"]
        
        resposta = f"💸 **Total de gastos** no período de {periodo}: **R$ {total_gasto:,.2f}**\n"
        if analise.get("categoria_nome"):
            resposta += f"Categoria/Termo buscado: **{analise['categoria_nome']}**\n"
        if analise.get("descricao_texto"):
            resposta += f"Detalhe: **{analise['descricao_texto']}**\n"
        
        total_itens = len(dados_filtrados)
        resposta += f"📝 Total de lançamentos encontrados: **{total_itens}**\n"

        if 0 < total_itens:
            resposta += "\n🔍 **Detalhes dos Lançamentos:**\n"
            for item in dados_filtrados[:10]:
                desc = item.get("descricao", "Sem descrição")
                valor = float(item.get("total", 0))
                data_lancamento = item.get("data_competencia", item.get("data_vencimento", ""))
                resposta += f"- {data_lancamento}: {desc} (R$ {valor:,.2f})\n"
                
        return resposta