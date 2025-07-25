# modules/smart_analyzer.py
from datetime import datetime, timedelta
import unicodedata

def normalizar(texto):
    if not texto: return ""
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII').lower().strip()

class SmartAnalyzer:
    def __init__(self):
        pass

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
        else: # Padrão: Últimos 30 dias
            data_de = hoje - timedelta(days=30)
            data_ate = hoje
            
        return data_de.strftime("%Y-%m-%d"), data_ate.strftime("%Y-%m-%d")

    def analisar_pergunta(self, pergunta, lista_categorias_completa):
        pergunta_norm = normalizar(pergunta)
        data_de, data_ate = self.interpretar_periodo(pergunta)

        categoria_encontrada = None
        candidatas = []
        # Procura na lista de categorias que já baixamos
        for categoria_obj in lista_categorias_completa:
            cat_norm = normalizar(categoria_obj['nome'])
            palavras_cat = cat_norm.split()
            if all(palavra in pergunta_norm for palavra in palavras_cat):
                candidatas.append((categoria_obj, len(cat_norm)))
        
        if candidatas:
            # Pega a melhor correspondência (a mais longa)
            categoria_encontrada = sorted(candidatas, key=lambda x: x[1], reverse=True)[0][0]

        # Extrai a descrição (o que sobra da pergunta)
        descricao = pergunta
        termos_para_remover = [
            (categoria_encontrada['nome'] if categoria_encontrada else None),
            "quanto gastei de", "quanto gastei com", "gastos com", "custo de", 
            "despesas com", "este ano", "esse ano", "este mes", "esse mes", 
            "mes passado", "?"
        ]
        for termo in termos_para_remover:
            if termo: descricao = descricao.replace(termo, "").strip()
        
        return {
            "data_de": data_de,
            "data_ate": data_ate,
            "categoria_obj": categoria_encontrada,
            "descricao_texto": descricao or None
        }

    def formatar_resposta(self, dados, analise):
        if not dados or not dados.get("itens"):
            return "❌ Nenhum gasto encontrado para os filtros informados."
        
        itens = dados["itens"]
        total_gasto = sum(float(item.get("total", 0)) for item in itens)
        
        resposta = f"💸 **Total de gastos: R$ {total_gasto:,.2f}**\n"
        if analise.get("categoria_obj"):
            resposta += f"Categoria: **{analise['categoria_obj']['nome']}**\n"
        if analise.get("descricao_texto"):
            resposta += f"Descrição: **{analise['descricao_texto']}**\n"
        
        resposta += f"📝 **{len(itens)}** lançamentos encontrados.\n\n"
        for item in itens[:10]:
            data = item.get("data_competencia", item.get("data_vencimento", ""))
            desc = item.get("descricao", "Sem descrição")
            valor = float(item.get("total", 0))
            resposta += f"- *{data}*: {desc} (R$ {valor:,.2f})\n"
            
        return resposta
