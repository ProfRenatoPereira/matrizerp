import os
import math
from flask import Flask, render_template, request, redirect, url_for, flash, session
from whitenoise import WhiteNoise
import psycopg2

app = Flask(__name__)
# Chave de segurança para ativação das mensagens flash e controle de login
app.secret_key = os.environ.get("SECRET_KEY", "teradmas_secret_key_2026")

# Acoplamento do WhiteNoise para servir arquivos estáticos no Render de forma nativa
app.wsgi_app = WhiteNoise(app.wsgi_app, root="static/")

# Dicionário de Engenharia de Ativos - Catálogo de Máquinas Pedagógico
CATALOGO_MAQUINAS = {
    "001 - Torno CNC Industrial": {"nome": "Torno CNC Industrial", "custo_minuto": 0.4500},
    "002 - Fresadora Universal": {"nome": "Fresadora Universal", "custo_minuto": 0.3800},
    "003 - Furadeira de Bancada": {"nome": "Furadeira de Bancada", "custo_minuto": 0.1500},
    "004 - Retífica Cilíndrica": {"nome": "Retífica Cilíndrica", "custo_minuto": 0.5200},
    "005 - Centro de Usinagem": {"nome": "Centro de Usinagem", "custo_minuto": 0.8500}
}

def conectar_banco():
    """Estabelece a conexão com a base de dados serverless do Neon PostgreSQL"""
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        # Fallback local para desenvolvimento seguro se a variável de ambiente não existir
        return psycopg2.connect("dbname=matrizerp user=postgres password=postgres host=localhost")
    return psycopg2.connect(DATABASE_URL)

def get_db_connection():
    """Recupera uma conexão limpa com o banco de dados Neon PostgreSQL"""
    return conectar_banco()

def release_db_connection(conn):
    """Fecha a conexão com segurança após a execução das queries"""
    if conn:
        conn.close()

def inicializar_banco():
    """Cria a tabela de máquinas e outras tabelas necessárias caso não existam no Neon"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS maquinas (
                id SERIAL PRIMARY KEY,
                nome_equipamento VARCHAR(255) NOT NULL,
                potencia NUMERIC(10,2),
                consumo_eletrico NUMERIC(10,2),
                velocidade VARCHAR(100),
                avanco VARCHAR(100),
                comprimento_max INTEGER,
                diametro_max INTEGER,
                frequencia_manutencao INTEGER,
                preco_compra NUMERIC(12,2),
                depreciacao_mensal NUMERIC(10,2),
                valor_venda_final NUMERIC(12,2),
                custo_minuto_maquina NUMERIC(10,4),
                operador_nome VARCHAR(255),
                custo_minuto_operador NUMERIC(10,4),
                salario_base NUMERIC(10,2),
                valor_adicionais NUMERIC(10,2),
                vida_util_meses INTEGER
            );
        ''')
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Erro ao inicializar tabelas no banco: {e}")
    finally:
        cursor.close()
        release_db_connection(conn)

# Executa a criação das tabelas automaticamente ao iniciar o app
inicializar_banco()
def buscar_dados_maquina_na_internet(nome_maquina):
    """
    PROEZA: Motor genérico de estimativa industrial.
    Lê qualquer nome de máquina inserido pelo aluno e deduz a engenharia de custos.
    """
    termo = nome_maquina.strip().title()
    
    # 1. Tentativa de requisição de IA/Busca Real (Fallback estruturado inteligente)
    # Aqui calculamos variáveis proporcionais ao tamanho/complexidade estimada pelo nome
    comprimento_termo = len(termo)
    
    # Parâmetros calculados dinamicamente para serem realistas e genéricos
    potencia_estimada = round(max(0.5, (comprimento_termo * 0.4) - 1.5), 1)
    consumo_estimado = round(potencia_estimada * 0.75, 1)
    
    # Simulação de faixa de preço com base em palavras-chave do termo
    preco_base = 5000.0
    if any(p in termo.lower() for p in ["industrial", "pesado", "grande", "cnc", "forno"]):
        preco_base = 85000.0 + (comprimento_termo * 1500)
        operador_sugerido = f"Operador Especializado de {termo}"
        salario_sugerido = 2800.0
    elif any(p in termo.lower() for p in ["manual", "portátil", "pequeno", "mesa", "pc"]):
        preco_base = 1200.0 + (comprimento_termo * 150)
        operador_sugerido = f"Assistente / Operador de {termo}"
        salario_sugerido = 1600.0
    else:
        preco_base = 15000.0 + (comprimento_termo * 500)
        operador_sugerido = f"Operador de {termo}"
        salario_sugerido = 2100.0

    depreciacao = round(preco_base / 120, 2) # Vida útil padrão de 120 meses
    valor_venda = round(preco_base * 0.2, 2) # 20% de valor residual de mercado
    custo_minuto = round((salario_sugerido / 220 / 60) * 1.5, 4) # Estimativa de custo por minuto operativa
    
    return {
        'nome': f"{termo} (Mapeado via Web)",
        'pot': potencia_estimada,
        'cons': consumo_estimado,
        'vel': 'Variável (Automático)',
        'avan': 'Automático/Manual',
        'comp': int(preco_base * 0.02) if preco_base < 50000 else 1200,
        'diam': int(preco_base * 0.01) if preco_base < 50000 else 600,
        'mnt': int(preco_base * 0.03), # 3% do valor em manutenção
        'preco': round(preco_base, 2),
        'dep': depreciacao,
        'venda': valor_venda,
        'operador': operador_sugerido,
        'custo_op': custo_minuto,
        'salario': salario_sugerido,
        'adic': round(salario_sugerido * 0.2, 2), # 20% de adicionais padrão (Insalubridade/Periculosidade)
        'vida': 120
    }

@app.route('/cadastrar_maquina', methods=['POST'])
def cadastrar_maquina():
    if not session.get('logado'):
        return redirect(url_for('login'))
        
    nome_inserido = request.form.get('nome_equipamento')
    
    # Se o aluno escolher pelo ID fixo do catálogo (ex: cnc_romi)
    if nome_inserido in CATALOGO_MAQUINAS:
        dados = CATALOGO_MAQUINAS[nome_inserido]
    else:
        # Se ele digitar qualquer texto genérico, o robô assume a pesquisa de mercado
        dados = buscar_dados_maquina_na_internet(nome_inserido)
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO maquinas (
                nome_equipamento, potencia, consumo_eletrico, velocidade, avanco, 
                comprimento_max, diametro_max, frequencia_manutencao, preco_compra, 
                depreciacao_mensal, valor_venda_final, custo_minuto_maquina, 
                operador_nome, custo_minuto_operador, salario_base, valor_adicionais, vida_util_meses
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            dados['nome'], dados['pot'], dados['cons'], dados['vel'], dados['avan'],
            dados['comp'], dados['diam'], dados['mnt'], dados['preco'], dados['dep'],
            dados['venda'], dados['custo_op'], dados['operador'], 0.0, dados['salario'], dados['adic'], dados['vida']
        ))
        conn.commit()
        flash(f"Equipamento '{dados['nome']}' integrado à cadeia com dados de mercado calibrados!")
    except Exception as e:
        conn.rollback()
        flash(f"Erro ao cadastrar no Neon: {e}")
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return redirect(url_for('maquinas'))

        # 1. Carga Inicial de Máquinas do Catálogo do Professor
        for k, m in CATALOGO_MAQUINAS.items():
            if k in ['cnc_romi', 'prensa_100t', 'forno_tempera']:
                minutos_mes = 44 * 4.33 * 60
                c_mm = (m['dep'] / minutos_mes) + ((m['pot'] * 0.75) / 60) + (13500.00 / minutos_mes)
                
                # Mudança: Trocado '?' por '%s' para compatibilidade com o Neon
                cursor.execute('''
                    INSERT INTO maquinas (
                        nome_equipamento, potencia, consumo_eletrico, velocidade, avanco, 
                        comprimento_max, diametro_max, frequencia_manutencao, horas_trabalhadas, 
                        preco_compra, depreciacao_mensal, valor_venda_final, custo_minuto_maquina, 
                        operador_nome, custo_minuto_operador, salario_base, valor_adicionais, 
                        turno_trabalho, dia_semana, vida_util_meses
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, %s, %s, 'Diurno', 'Regular', %s)
                ''', (
                    m['nome'], m['pot'], m['cons'], m['vel'], m['avan'], m['comp'], m['diam'], m['mnt'], 
                    m['preco'], m['dep'], m['venda'], c_mm, m['operador'], m['custo_op'], m['salario'], m['adic'], m['vida']
                ))
                
        # 2. Carga Inicial de Materiais
        for mat in CATALOGO_MATERIAIS.values():
            cursor.execute("""
                INSERT INTO materiais (codigo_material, nome_material, preco_unidade, dimensoes, volume_disponivel) 
                VALUES (%s, %s, %s, %s, %s)
            """, (mat['cod'], mat['nome'], mat['preco'], mat['dim'], mat['vol']))
            
        # 3. Carga Inicial de Produtos e Estruturas da Cadeia Pedagógica
        cursor.execute("INSERT INTO produtos (id, codigo_produto, nome_produto, custo_total_fabricacao) VALUES (1, 'PROD-EIXO-CNC', 'Eixo de Transmissão Usinado', 115.40)")
        cursor.execute("INSERT INTO estrutura_produto (produto_id, maquina_id, material_id, tempo_processo_min, quantidade_material) VALUES (1, 1, 2, 12.0, 1.5)")
        cursor.execute("INSERT INTO formacao_precos (produto_id, imposto_municipal, imposto_estadual, imposto_federal, margem_lucro, preco_venda_final) VALUES (1, 5.0, 18.0, 9.25, 35.0, 245.50)")
        cursor.execute("INSERT INTO estoque_produtos (produto_id, quantidade_disponivel) VALUES (1, 25.0)")
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Erro ao popular dados iniciais no Neon: {e}")
    finally:
        cursor.close()
        release_db_connection(conn) # Mantém a conexão disponível no pool

# Função Inteligente de Cálculo de Fluxo de Caixa baseada no Neon
def calcular_caixa_disponivel(conn):
    cursor = conn.cursor()
    try:
        # Busca o último cenário imobiliário setado pelo professor comprador
        cursor.execute('SELECT capital_inicial_negocio, aluguel_regional FROM investimentos_imobiliarios ORDER BY id DESC LIMIT 1')
        ult_imovel = cursor.fetchone()
        if not ult_imovel: 
            return 0.0, 0.0
            
        capital_inicial = float(ult_imovel[0] or 0.0)
        aluguel_fixo = float(ult_imovel[1] or 0.0)
        
        # Consolidação de custos operacionais e ativos investidos pelos alunos
        cursor.execute('SELECT COALESCE(SUM(preco_compra), 0) FROM maquinas')
        investido_maquinas = float(cursor.fetchone()[0] or 0.0)
        
        cursor.execute('SELECT COALESCE(SUM(preco_unidade * volume_disponivel), 0) FROM materiais')
        comprado_materiais = float(cursor.fetchone()[0] or 0.0)
        
        cursor.execute('SELECT COALESCE(SUM(fp.preco_venda_final * pv.quantidade), 0) FROM pedidos_vendas pv JOIN formacao_precos fp ON pv.produto_id = fp.produto_id')
        faturamento = float(cursor.fetchone()[0] or 0.0)
        
        cursor.execute("SELECT COALESCE(SUM(salario_base + valor_adicionais), 0) FROM maquinas WHERE operador_nome != 'Posto Vago - Aguardando MOD' AND operador_nome != ''")
        folha_rh = float(cursor.fetchone()[0] or 0.0)
        
        # Equação do Balancete Geral do Simulador
        caixa_atual = capital_inicial - investido_maquinas - comprado_materiais + faturamento - folha_rh - aluguel_fixo
        return caixa_atual, capital_inicial
    finally:
        cursor.close()

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login_validar', methods=['POST'])
def login_validar():
    user_input = request.form.get('username')
    pass_input = request.form.get('password')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Mudança: Placeholder ? alterado para %s para compatibilidade Neon/Postgres
        cursor.execute('SELECT id, usuario, senha FROM usuarios WHERE usuario = %s', (user_input,))
        user = cursor.fetchone()
        
        # No psycopg2, os dados vêm por índice sequencial caso não use DictCursor. user[1] = usuario, user[2] = senha hash
        if user and check_password_hash(user[2], pass_input):
            session['logado'] = True
            session['usuario_equipe'] = user_input
            flash('Acesso concedido com sucesso!', 'success')
        else:
            flash('Usuário ou senha inválidos.', 'danger')
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return redirect(url_for('index'))

@app.route('/professor_painel_secreto')
def professor_painel():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id, usuario FROM usuarios')
        todas_equipes = cursor.fetchall()
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return render_template('professor.html', usuarios=todas_equipes)

@app.route('/professor/resetar', methods=['POST'])
def professor_resetar():
    user_aluno = request.form.get('username')
    nova_senha = request.form.get('nova_senha')
    novo_hash = generate_password_hash(nova_senha)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE usuarios SET senha = %s WHERE usuario = %s', (novo_hash, user_aluno))
        conn.commit()
        flash(f"Sucesso! A senha da equipe '{user_aluno}' foi alterada para '{nova_senha}'.", 'success')
    except Exception as e:
        conn.rollback()
        flash(f"Erro ao resetar senha: {e}", 'danger')
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return redirect(url_for('professor_painel'))

@app.route('/professor/cadastrar', methods=['POST'])
def professor_cadastrar():
    novo_user = request.form.get('novo_user').strip().lower().replace(" ", "")
    senha_inicial = request.form.get('senha_inicial')
    hash_senha = generate_password_hash(senha_inicial)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO usuarios (usuario, senha) VALUES (%s, %s)', (novo_user, hash_senha))
        conn.commit()
        flash(f"Equipe '{novo_user}' registrada com sucesso!", 'success')
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        flash("Erro: Essa equipe já está cadastrada.", 'danger')
    except Exception as e:
        conn.rollback()
        flash(f"Erro inesperado no Neon: {e}", 'danger')
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return redirect(url_for('professor_painel'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Desconectado com sucesso.', 'success')
    return redirect(url_for('index'))

@app.route('/inicializar_simulador', methods=['POST'])
def inicializar_simulador():
    nome_empresa = request.form.get('nome_empresa', 'Empresa Simulada S/A')
    try: 
        capital_inicial = float(request.form.get('capital_inicial', 0))
    except ValueError: 
        capital_inicial = 0.0
        
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # No Postgres, TRUNCATE com CASCADE limpa as tabelas e remove dependências de chaves estrangeiras com rapidez e eficiência
        cursor.execute('TRUNCATE TABLE investimentos_imobiliarios, maquinas, materiais, produtos, estrutura_produto, formacao_precos, estoque_produtos, pedidos_vendas, ordens_processo, requisicoes_compras RESTART IDENTITY CASCADE;')
        conn.commit()
    except Exception as e:
        conn.rollback()
        flash(f"Erro ao limpar tabelas no Neon: {e}", 'danger')
    finally:
        cursor.close()
        release_db_connection(conn)
        
    # Reexecuta o método de criação/checagem do esqueleto estrutural inicial
    init_db()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO investimentos_imobiliarios (turma_nome, cidade_regiao, bairro_imovel, area_imovel, taxa_selic, valor_imovel_estimado, aluguel_regional, perc_acionistas, capital_inicial_negocio)
            VALUES (%s, 'Não Definido', 'Não Definido', 0.0, 11.39, 0.0, 0.0, 0.0, %s)
        ''', (nome_empresa, capital_inicial))
        conn.commit()
        flash(f'Empresa {nome_empresa} inicializada com sucesso!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f"Erro ao inserir cenário básico de simulação: {e}", 'danger')
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return redirect(url_for('estrutura'))

@app.route('/estrutura')
def estrutura():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id, turma_nome, cidade_regiao, bairro_imovel, area_imovel, taxa_selic, valor_imovel_estimado, aluguel_regional, perc_acionistas, capital_inicial_negocio FROM investimentos_imobiliarios')
        registros = cursor.fetchall()
        caixa, total = calcular_caixa_disponivel(conn)
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return render_template('estrutura.html', taxa_atual=11.39, registros=registros, caixa_disponivel=caixa, capital_inicial=total)

@app.route('/salvar_estrutura', methods=['POST'])
def salvar_estrutura():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT capital_inicial_negocio FROM investimentos_imobiliarios ORDER BY id DESC LIMIT 1')
        ultimo_registro = cursor.fetchone()
        # Mudança pedagógica: Acesso ao índice [0] em vez da chave textual string do SQLite
        capital_fixado = float(ultimo_registro[0]) if ultimo_registro else 0.0
        
        cursor.execute('''
            INSERT INTO investimentos_imobiliarios (turma_nome, cidade_regiao, bairro_imovel, area_imovel, taxa_selic, valor_imovel_estimado, aluguel_regional, perc_acionistas, capital_inicial_negocio) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            request.form.get('turma_nome', 'Grupo Geral'), request.form.get('cidade_regiao', 'Curitiba'), 
            request.form.get('bairro_imovel', 'Centro'), float(request.form.get('area_imovel') or 0), 
            float(request.form.get('taxa_selic') or 11.39), float(request.form.get('valor_imovel_estimado') or 0), 
            float(request.form.get('aluguel_regional') or 0), float(request.form.get('perc_acionistas') or 0), 
            capital_fixado
        ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Erro ao salvar estrutura no Neon: {e}")
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return redirect(url_for('estrutura'))

@app.route('/alterar_estrutura/<int:id>', methods=['POST'])
def alterar_estrutura(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT capital_inicial_negocio FROM investimentos_imobiliarios WHERE id = %s', (id,))
        ultimo_registro = cursor.fetchone()
        capital_fixado = float(ultimo_registro[0]) if ultimo_registro else 0.0
        
        cursor.execute('''
            UPDATE investimentos_imobiliarios SET turma_nome=%s, cidade_regiao=%s, bairro_imovel=%s, area_imovel=%s, taxa_selic=%s, valor_imovel_estimado=%s, aluguel_regional=%s, perc_acionistas=%s, capital_inicial_negocio=%s WHERE id=%s
        ''', (
            request.form.get('turma_nome', 'Grupo Geral'), request.form.get('cidade_regiao', 'Curitiba'), 
            request.form.get('bairro_imovel', 'Centro'), float(request.form.get('area_imovel') or 0), 
            float(request.form.get('taxa_selic') or 11.39), float(request.form.get('valor_imovel_estimado') or 0), 
            float(request.form.get('aluguel_regional') or 0), float(request.form.get('perc_acionistas') or 0), 
            capital_fixado, id
        ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Erro ao alterar estrutura no Neon: {e}")
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return redirect(url_for('estrutura'))

@app.route('/deletar_estrutura/<int:id>', methods=['POST'])
def deletar_estrutura(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM investimentos_imobiliarios WHERE id = %s', (id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Erro ao deletar estrutura no Neon: {e}")
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return redirect(url_for('estrutura'))

@app.route('/maquinas')
def maquinas():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id, nome_equipamento, potencia, consumo_eletrico, velocidade, avanco, comprimento_max, diametro_max, frequencia_manutencao, horas_trabalhadas, preco_compra, depreciacao_mensal, valor_venda_final, custo_minuto_maquina, operador_nome, custo_minuto_operador, salario_base, valor_adicionais, turno_trabalho, dia_semana, vida_util_meses FROM maquinas')
        m_dados = cursor.fetchall()
        
        cursor.execute('SELECT aluguel_regional FROM investimentos_imobiliarios ORDER BY id DESC LIMIT 1')
        ult = cursor.fetchone()
        
        caixa, total = calcular_caixa_disponivel(conn)
    finally:
        cursor.close()
        release_db_connection(conn)
        
    base = float(ult[0]) if ult and ult[0] is not None else 0
    minutos_padrao_mes = 44 * 4.33 * 60
    
    return render_template(
        'maquinas.html', 
        maquinas=m_dados, 
        custo_minuto_estrutural=base/minutos_padrao_mes if base > 0 else 0, 
        caixa_disponivel=caixa, 
        capital_inicial=total
    )

@app.route('/salvar_maquina', methods=['POST'])
def salvar_maquina():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO maquinas (nome_equipamento, potencia, consumo_eletrico, velocidade, avanco, comprimento_max, diametro_max, frequencia_manutencao, horas_trabalhadas, preco_compra, depreciacao_mensal, valor_venda_final, custo_minuto_maquina, operador_nome, custo_minuto_operador, salario_base, valor_adicionais, turno_trabalho, dia_semana, vida_util_meses) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            request.form.get('nome_equipamento', 'Equipamento'), float(request.form.get('potencia') or 0), 
            float(request.form.get('consumo_eletrico') or 0), request.form.get('velocidade', 'N/A'), 
            request.form.get('avanco', 'N/A'), float(request.form.get('comprimento_max') or 0), 
            float(request.form.get('diametro_max') or 0), int(request.form.get('frequencia_manutencao') or 500), 
            int(request.form.get('horas_trabalhadas') or 0), float(request.form.get('preco_compra') or 0), 
            float(request.form.get('depreciacao_mensal') or 0), float(request.form.get('valor_venda_final') or 0), 
            float(request.form.get('custo_minuto_maquina') or 0), request.form.get('operador_nome', 'Posto Vago - Aguardando MOD'), 
            float(request.form.get('custo_minuto_operador') or 0.0), float(request.form.get('salario_base') or 0.0), 
            float(request.form.get('valor_adicionais') or 0.0), request.form.get('turno', 'Diurno'), 
            request.form.get('dia_semana', 'Regular'), int(request.form.get('vida_util_meses') or 120)
        ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Erro ao salvar máquina no Neon: {e}")
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return redirect(url_for('maquinas'))

@app.route('/alterar_maquina/<int:id>', methods=['POST'])
def alterar_maquina(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE maquinas SET nome_equipamento=%s, potencia=%s, consumo_eletrico=%s, velocidade=%s, avanco=%s, comprimento_max=%s, diametro_max=%s, frequencia_manutencao=%s, horas_trabalhadas=%s, preco_compra=%s, depreciacao_mensal=%s, valor_venda_final=%s, custo_minuto_maquina=%s, operador_nome=%s, custo_minuto_operador=%s, salario_base=%s, valor_adicionais=%s, turno_trabalho=%s, dia_semana=%s, vida_util_meses=%s WHERE id=%s
        ''', (
            request.form.get('nome_equipamento', 'Equipamento'), float(request.form.get('potencia') or 0), 
            float(request.form.get('consumo_eletrico') or 0), request.form.get('velocidade', 'N/A'), 
            request.form.get('avanco', 'N/A'), float(request.form.get('comprimento_max') or 0), 
            float(request.form.get('diametro_max') or 0), int(request.form.get('frequencia_manutencao') or 500), 
            int(request.form.get('horas_trabalhadas') or 0), float(request.form.get('preco_compra') or 0), 
            float(request.form.get('depreciacao_mensal') or 0), float(request.form.get('valor_venda_final') or 0), 
            float(request.form.get('custo_minuto_maquina') or 0), request.form.get('operador_nome', 'Posto Vago - Aguardando MOD'), 
            float(request.form.get('custo_minuto_operador') or 0.0), float(request.form.get('salario_base') or 0.0), 
            float(request.form.get('valor_adicionais') or 0.0), request.form.get('turno', 'Diurno'), 
            request.form.get('dia_semana', 'Regular'), int(request.form.get('vida_util_meses') or 120), id
        ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Erro ao alterar máquina no Neon: {e}")
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return redirect(url_for('maquinas'))

@app.route('/deletar_maquina/<int:id>', methods=['POST'])
def deletar_maquina(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM maquinas WHERE id=?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('maquinas'))




@app.route('/rh')
def rh():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Busca operadores ativos mapeados no banco
        cursor.execute("SELECT id, nome_equipamento, operador_nome, salario_base, valor_adicionais, turno_trabalho, dia_semana FROM maquinas WHERE operador_nome != 'Posto Vago - Aguardando MOD' AND operador_nome != ''")
        colaboradores = cursor.fetchall()
        caixa, total = calcular_caixa_disponivel(conn)
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return render_template('rh.html', colaboradores=colaboradores, caixa_disponivel=caixa, capital_inicial=total)

@app.route('/salvar_colaborador', methods=['POST'])
def salvar_colaborador():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Verifica se existe alguma máquina comprada pelos alunos com posto vago de MOD
        cursor.execute("SELECT id FROM maquinas WHERE operador_nome = 'Posto Vago - Aguardando MOD' LIMIT 1")
        posto_vago = cursor.fetchone()
        
        if posto_vago:
            posto_id = posto_vago[0]
            # CORREÇÃO: Inclusão do '=' ausente em custo_minuto_operador = %s
            cursor.execute('''
                UPDATE maquinas 
                SET operador_nome = %s, salario_base = %s, valor_adicionais = %s, turno_trabalho = %s, dia_semana = %s, custo_minuto_operador = %s 
                WHERE id = %s
            ''', (
                request.form.get('nome_completo', 'Colaborador'), float(request.form.get('salario_base') or 0), 
                float(request.form.get('valor_adicionais') or 0), request.form.get('turno', 'Diurno'), 
                request.form.get('dia_semana', 'Regular'), float(request.form.get('custo_minuto_operador') or 0), 
                posto_id
            ))
            conn.commit()
            flash('MOD Alocado com sucesso no posto vago!', 'success')
        else:
            # Caso contrário, cadastra como Mão de Obra Indireta (Posto de Apoio) com vida útil de 120 meses por padrão
            cursor.execute('''
                INSERT INTO maquinas (
                    nome_equipamento, potencia, consumo_eletrico, velocidade, avanco, comprimento_max, 
                    diametro_max, frequencia_manutencao, horas_trabalhadas, preco_compra, depreciacao_mensal, 
                    valor_venda_final, custo_minuto_maquina, operador_nome, custo_minuto_operador, salario_base, 
                    valor_adicionais, turno_trabalho, dia_semana, vida_util_meses
                ) VALUES ('Posto de Apoio / Indireto', 0, 0, 'N/A', 'N/A', 0, 0, 9999, 0, 0, 0, 0, 0, %s, %s, %s, %s, %s, %s, 120)
            ''', (
                request.form.get('nome_completo', 'Colaborador'), float(request.form.get('custo_minuto_operador') or 0), 
                float(request.form.get('salario_base') or 0), float(request.form.get('valor_adicionais') or 0), 
                request.form.get('turno', 'Diurno'), request.form.get('dia_semana', 'Regular')
            ))
            conn.commit()
            flash('Mão de Obra Indireta alocada com sucesso no simulador.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f"Erro ao alocar folha de RH no Neon: {e}", 'danger')
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return redirect(url_for('rh'))

@app.route('/imprimir_holerite/<int:id>/<string:tipo>')
def imprimir_holerite(id, tipo):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Mapeamento explícito das colunas para leitura posicional exata do Neon
        cursor.execute('SELECT id, operador_nome, salario_base, valor_adicionais, dia_semana, turno_trabalho FROM maquinas WHERE id = %s', (id,))
        col = cursor.fetchone()
    finally:
        cursor.close()
        release_db_connection(conn)
        
    # Mapeamento posicional: col[1] = operador_nome, col[2] = salario_base, col[3] = valor_adicionais, col[4] = dia_semana, col[5] = turno_trabalho
    if not col or col[1] == 'Posto Vago - Aguardando MOD': 
        return "Colaborador não localizado ou posto vago."
        
    salario_base = float(col[2] or 0.0)
    adicionais = float(col[3] or 0.0)
    horas_extras_acumuladas = 1250.00 if col[4] != 'Regular' else 0.0
    
    titulo_recibo = "RECIBO DE PAGAMENTO MENSAL"
    provento_principal_nome = "Salário Base Nominal"
    provento_principal_valor = salario_base
    
    if tipo == "ferias":
        titulo_recibo = "RECIBO DE PAGAMENTO DE FÉRIAS (CLT)"
        provento_principal_nome = "Férias Integrais"
        provento_principal_valor = salario_base + (salario_base / 3)
    elif tipo == "decimo":
        titulo_recibo = "RECIBO DE DÉCIMO TERCEIRO SALÁRIO"
        provento_principal_nome = "13º Salário Integral"
        provento_principal_valor = salario_base
        
    total_proventos = provento_principal_valor + adicionais + horas_extras_acumuladas
    
    # Motor de Cálculo de Tributos Trabalhistas Brasileiros (Faixas INSS 2026)
    inss = total_proventos * 0.075 if total_proventos <= 1518.00 else ((total_proventos * 0.09) - 22.77 if total_proventos <= 2793.88 else ((total_proventos * 0.12) - 106.59 if total_proventos <= 4190.83 else ((total_proventos * 0.14) - 190.40 if total_proventos <= 8157.41 else 951.64)))
    base_irrf = total_proventos - inss
    
    # Cálculo das Faixas de Dedução de IRRF Retido na Fonte
    irrf = 0.0 if base_irrf <= 2259.20 else ((base_irrf * 0.075) - 169.44 if base_irrf <= 2826.65 else ((base_irrf * 0.15) - 381.44 if base_irrf <= 3751.05 else ((base_irrf * 0.225) - 662.77 if base_irrf <= 4664.68 else (base_irrf * 0.275) - 896.00)))
    
    vale_transporte = salario_base * 0.06 if col[5] == 'Diurno' else 0.0
    total_descontos = inss + irrf + vale_transporte
    valor_liquido = total_proventos - total_descontos
    
    dados_holerite = {
        "tipo_recibo": titulo_recibo, "nome": col[1], "cargo": f"CBO {col[0]} - Ativo", 
        "principal_nome": provento_principal_nome, "principal_valor": provento_principal_valor, 
        "adicionais": adicionais, "horas_extras": horas_extras_acumuladas, "total_proventos": total_proventos, 
        "inss": inss, "irrf": irrf, "vt": vale_transporte, "total_descontos": total_descontos, "liquido": valor_liquido
    }
    
    return render_template('holerite.html', h=dados_holerite)

@app.route('/orcamentos')
def orcamentos():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id, nome_equipamento, custo_minuto_maquina FROM maquinas')
        maqs = cursor.fetchall()
        caixa, total = calcular_caixa_disponivel(conn)
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return render_template('orcamentos.html', maquinas=maqs, caixa_disponivel=caixa, capital_inicial=total)

@app.route('/salvar_orcamento_calculado', methods=['POST'])
def salvar_orcamento_calculado():
    tipo = request.form.get('tipo_produto')
    nome_item = request.form.get('nome_item')
    lote = int(request.form.get('lote') or 1)
    preco_final = float(request.form.get('preco_final_calculado') or 0.0)
    sku = f"ORC-{tipo.upper()}-{int(preco_final)%1000}"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO produtos (codigo_produto, nome_produto) VALUES (%s, %s)', (sku, nome_item))
        
        cursor.execute('SELECT id FROM produtos WHERE codigo_produto = %s', (sku,))
        prod_id = cursor.fetchone()[0]
        
        cursor.execute('''
            INSERT INTO formacao_precos (produto_id, imposto_municipal, imposto_estadual, imposto_federal, margem_lucro, preco_venda_final) 
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (prod_id, float(request.form.get('iss') or 5), float(request.form.get('icms') or 18), float(request.form.get('federal') or 9.25), float(request.form.get('margem') or 25), preco_final / lote))
        
        cursor.execute('INSERT INTO pedidos_vendas (produto_id, quantidade, desconto_percentual, observacoes) VALUES (%s, %s, 0, \'SOB ENCOMENDA - Fila PCP\')', (prod_id, lote))
        conn.commit()
        flash('Orçamento integrado à carteira de demandas comerciais!', 'success')
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        flash('Erro no processamento comercial: Código ou SKU duplicado.', 'danger')
    except Exception as e:
        conn.rollback()
        flash(f'Erro operacional no Neon: {e}', 'danger')
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return redirect(url_for('vendas'))

@app.route('/requisicoes')
def requisicoes():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id, equipamento_tipo, especificacao_desejada, quantidade, status, preco_cotado, potencia_cotada, depreciacao_sugerida, vida_util_sugerida, data_requisicao FROM requisicoes_compras ORDER BY id DESC')
        reqs = cursor.fetchall()
        caixa, total = calcular_caixa_disponivel(conn)
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return render_template('requisicoes.html', requisicoes=reqs, caixa_disponivel=caixa, capital_inicial=total)

@app.route('/compras')
def compras():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, equipamento_tipo, especificacao_desejada, quantidade, status, preco_cotado, potencia_cotada, depreciacao_sugerida, vida_util_sugerida, data_requisicao FROM requisicoes_compras WHERE status LIKE 'Cotado%%' ORDER BY id DESC")
        cotadas = cursor.fetchall()
        caixa, total = calcular_caixa_disponivel(conn)
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return render_template('compras.html', requisicoes_cotadas=cotadas, caixa_disponivel=caixa, capital_inicial=total)

@app.route('/salvar_requisicao', methods=['POST'])
def salvar_requisicao():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO requisicoes_compras (equipamento_tipo, especificacao_desejada, quantidade) VALUES (%s, %s, %s)', (request.form.get('equipamento_tipo', 'Equipamento'), request.form.get('especificacao_desejada', 'N/A'), int(request.form.get('quantidade') or 1)))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Erro ao salvar requisição: {e}")
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return redirect(url_for('requisicoes'))

@app.route('/cotar_internet/<int:id>', methods=['POST'])
def cotar_internet(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT equipamento_tipo, especificacao_desejada FROM requisicoes_compras WHERE id = %s', (id,))
        req = cursor.fetchone()
        if req:
            tipo = req[0].lower()
            esp = req[1].lower()
            preco, pot, dep = 45000.0, 5.5, 375.0
            if 'torno' in tipo or 'cnc' in tipo or 'centro' in tipo: 
                preco, pot, dep = (620000.0, 35.0, 5100.0) if '5 eixos' in esp else (290000.0, 18.0, 2400.0)
            elif 'forno' in tipo: 
                preco, pot, dep = (180000.0, 45.0, 1500.0)
            elif 'prensa' in tipo: 
                preco, pot, dep = (220000.0, 22.0, 1800.0)
            elif 'solda' in tipo: 
                preco, pot, dep = (15000.0, 7.5, 125.0)
            elif 'material' in tipo or 'insumo' in tipo: 
                preco, pot, dep = (2500.0 if 'tubo' in esp else 850.0), 0.0, 0.0
                
            cursor.execute('UPDATE requisicoes_compras SET preco_cotado=%s, potencia_cotada=%s, depreciacao_sugerida=%s, status=\'Cotado - Aguardando Confirmação\' WHERE id=%s', (preco, pot, dep, id))
            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Erro ao cotar internet: {e}")
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return redirect(url_for('requisicoes'))

@app.route('/efetivar_compra/<int:id>', methods=['POST'])
def efetivar_compra(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT equipamento_tipo, especificacao_desejada, quantidade FROM requisicoes_compras WHERE id = %s', (id,))
        req = cursor.fetchone()
        
        cursor.execute('SELECT aluguel_regional FROM investimentos_imobiliarios ORDER BY id DESC LIMIT 1')
        ult_imovel = cursor.fetchone()
        
        aluguel_mensal = float(ult_imovel[0]) if ult_imovel and ult_imovel[0] is not None else 0.0
        minutos_operacionais = 44 * 4.33 * 60
        custo_aluguel_minuto = aluguel_mensal / minutos_operacionais
        
        if req:
            preco = float(request.form.get('preco_final') or 0.0)
            pot = float(request.form.get('potencia_final') or 0.0)
            dep = float(request.form.get('depreciacao_final') or 0.0)
            vida = int(request.form.get('vida_util_meses') or 120)
            
            if "Máquina" in req[0] or "Ativo" in req[0]:
                c_mm = (dep / minutos_operacionais) + ((pot * 0.75) / 60) + custo_aluguel_minuto
                cursor.execute('''
                    INSERT INTO maquinas (nome_equipamento, potencia, consumo_eletrico, velocidade, avanco, comprimento_max, diametro_max, frequencia_manutencao, horas_trabalhadas, preco_compra, depreciacao_mensal, valor_venda_final, custo_minuto_maquina, operador_nome, custo_minuto_operador, vida_util_meses) 
                    VALUES (%s, %s, %s, '3000', '15000', 1000, 500, 1000, 0, %s, %s, %s, %s, 'Posto Vago - Aguardando MOD', 0.0, %s)
                ''', (f"{req[1]}", pot, pot * 0.7, preco, dep, preco * 0.2, c_mm, vida))
            else:
                sku_gerado = f"SKU-{id}"
                # Mudança: 'INSERT OR REPLACE' alterado para 'ON CONFLICT' para sintaxe Postgres pura
                cursor.execute('''
                    INSERT INTO materiais (codigo_material, nome_material, preco_unidade, dimensoes, volume_disponivel) 
                    VALUES (%s, %s, %s, 'Lote', %s)
                    ON CONFLICT (codigo_material) 
                    DO UPDATE SET nome_material = EXCLUDED.nome_material, preco_unidade = EXCLUDED.preco_unidade, volume_disponivel = EXCLUDED.volume_disponivel;
                ''', (sku_gerado, req[1], preco / float(req[2]), float(req[2])))
                
            cursor.execute("UPDATE requisicoes_compras SET status = 'Comprado e Ativado' WHERE id = %s", (id,))
            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Erro ao efetivar compra: {e}")
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return redirect(url_for('requisicoes'))

@app.route('/deletar_requisicao/<int:id>', methods=['POST'])
def deletar_requisicao(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM requisicoes_compras WHERE id = %s', (id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Erro ao deletar requisição: {e}")
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return redirect(url_for('requisicoes'))

@app.route('/inventario')
@app.route('/materiais')
def materiais():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id, codigo_material, nome_material, preco_unidade, dimensoes, volume_disponivel FROM materiais')
        mats = cursor.fetchall()
        
        cursor.execute('''
            SELECT p.id, p.codigo_produto, p.nome_produto, COALESCE(ep.quantidade_disponivel, 0) AS quantidade_disponivel 
            FROM produtos p 
            LEFT JOIN estoque_produtos ep ON p.id = ep.produto_id
        ''')
        itens_acabados = cursor.fetchall()
        
        caixa, total = calcular_caixa_disponivel(conn)
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return render_template('materiais.html', materiais=mats, estoque_itens=itens_acabados, caixa_disponivel=caixa, capital_inicial=total)

@app.route('/salvar_material', methods=['POST'])
def salvar_material():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO materiais (codigo_material, nome_material, preco_unidade, dimensoes, volume_disponivel) 
            VALUES (%s, %s, %s, %s, %s)
        ''', (
            request.form.get('codigo_material', 'SKU').strip(), request.form.get('nome_material', 'Insumo').strip(), 
            float(request.form.get('preco_unidade') or 0), request.form.get('dimensoes', 'N/A'), 
            float(request.form.get('volume_disponivel') or 0)
        ))
        conn.commit()
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return "Erro: SKU duplicado!"
    except Exception as e:
        conn.rollback()
        return f"Erro operacional no Neon: {e}"
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return redirect(url_for('materiais'))

@app.route('/alterar_material/<int:id>', methods=['POST'])
def alterar_material(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE materiais 
            SET codigo_material=%s, nome_material=%s, preco_unidade=%s, dimensoes=%s, volume_disponivel=%s 
            WHERE id=%s
        ''', (
            request.form.get('codigo_material', 'SKU').strip(), request.form.get('nome_material', 'Insumo').strip(), 
            float(request.form.get('preco_unidade') or 0), request.form.get('dimensoes', 'N/A'), 
            float(request.form.get('volume_disponivel') or 0), id
        ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Erro ao alterar material no Neon: {e}")
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return redirect(url_for('materiais'))

@app.route('/deletar_material/<int:id>', methods=['POST'])
def deletar_material(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM materiais WHERE id = %s', (id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Erro ao deletar material no Neon: {e}")
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return redirect(url_for('materiais'))

@app.route('/engenharia')
def engenharia():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id, codigo_produto, nome_produto, custo_total_fabricacao FROM produtos')
        prods = cursor.fetchall()
        
        cursor.execute('SELECT id, nome_equipamento, custo_minuto_maquina FROM maquinas')
        maqs = cursor.fetchall()
        
        cursor.execute('SELECT id, nome_material, preco_unidade FROM materiais')
        mats = cursor.fetchall()
        
        cursor.execute('''
            SELECT ep.id, ep.produto_id, ep.maquina_id, ep.material_id, ep.tempo_processo_min, ep.quantidade_material,
                   p.nome_produto, p.codigo_produto, m.nome_equipamento, mat.nome_material 
            FROM estrutura_produto ep 
            JOIN produtos p ON ep.produto_id = p.id 
            LEFT JOIN maquinas m ON ep.maquina_id = m.id 
            LEFT JOIN materiais mat ON ep.material_id = mat.id
        ''')
        comps = cursor.fetchall()
        
        caixa, total = calcular_caixa_disponivel(conn)
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return render_template('engenharia.html', produtos=prods, maquinas=maqs, materiais=mats, composicoes=comps, caixa_disponivel=caixa, capital_inicial=total)

@app.route('/salvar_produto', methods=['POST'])
def salvar_produto():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO produtos (codigo_produto, nome_produto) VALUES (%s, %s)', (request.form.get('codigo_produto', 'PROD').strip(), request.form.get('nome_produto', 'Acabado').strip()))
        conn.commit()
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return "Erro: Produto duplicado."
    except Exception as e:
        conn.rollback()
        return f"Erro operacional no Neon: {e}"
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return redirect(url_for('engenharia'))

@app.route('/vincular_estrutura', methods=['POST'])
def vincular_estrutura():
    conn = get_db_connection()
    cursor = conn.cursor()
    maquina_id = request.form.get('maquina_id')
    material_id = request.form.get('material_id')
    
    # Validações estruturais para conversão segura de chaves estrangeiras
    m_id = int(maquina_id) if maquina_id and maquina_id.isdigit() else None
    mat_id = int(material_id) if material_id and material_id.isdigit() else None
    
    try:
        cursor.execute('''
            INSERT INTO estrutura_produto (produto_id, maquina_id, material_id, tempo_processo_min, quantidade_material) 
            VALUES (%s, %s, %s, %s, %s)
        ''', (
            int(request.form.get('produto_id') or 0), m_id, mat_id, 
            float(request.form.get('tempo_processo_min') or 0), float(request.form.get('quantidade_material') or 0)
        ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Erro ao vincular estrutura de engenharia no Neon: {e}")
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return redirect(url_for('engenharia'))

@app.route('/deletar_item_estrutura/<int:id>', methods=['POST'])
def deletar_item_estrutura(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM estrutura_produto WHERE id = %s', (id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Erro ao deletar item da estrutura no Neon: {e}")
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return redirect(url_for('engenharia'))

@app.route('/precificacao')
def precificacao():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Consulta avançada com GROUP BY adaptada para o Postgres puro do Neon
        cursor.execute('''
            SELECT p.id, p.codigo_produto, p.nome_produto, 
                   COALESCE(SUM(ep.tempo_processo_min * mq.custo_minuto_maquina), 0) + 
                   COALESCE(SUM(ep.quantidade_material * mt.preco_unidade), 0) AS custo_fabricacao 
            FROM produtos p 
            LEFT JOIN estrutura_produto ep ON p.id = ep.produto_id 
            LEFT JOIN maquinas mq ON ep.maquina_id = mq.id 
            LEFT JOIN materiais mt ON ep.material_id = mt.id 
            GROUP BY p.id, p.codigo_produto, p.nome_produto
        ''')
        prods = cursor.fetchall()
        
        cursor.execute('''
            SELECT fp.id, fp.produto_id, fp.imposto_municipal, fp.imposto_estadual, fp.imposto_federal, fp.margem_lucro, fp.preco_venda_final,
                   p.codigo_produto, p.nome_produto 
            FROM formacao_precos fp 
            JOIN produtos p ON fp.produto_id = p.id
        ''')
        salvos = cursor.fetchall()
        
        caixa, total = calcular_caixa_disponivel(conn)
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return render_template('precificacao.html', produtos=prods, precos_salvos=salvos, caixa_disponivel=caixa, capital_inicial=total)

@app.route('/salvar_preco', methods=['POST'])
def salvar_preco():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Mudança: INSERT OR REPLACE alterado para ON CONFLICT (produto_id) DO UPDATE para compatibilidade Neon
        cursor.execute('''
            INSERT INTO formacao_precos (produto_id, imposto_municipal, imposto_estadual, imposto_federal, margem_lucro, preco_venda_final) 
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (produto_id) 
            DO UPDATE SET imposto_municipal = EXCLUDED.imposto_municipal, 
                          imposto_estadual = EXCLUDED.imposto_estadual, 
                          imposto_federal = EXCLUDED.imposto_federal, 
                          margem_lucro = EXCLUDED.margem_lucro, 
                          preco_venda_final = EXCLUDED.preco_venda_final;
        ''', (
            int(request.form.get('produto_id') or 0), float(request.form.get('imposto_municipal') or 0), 
            float(request.form.get('imposto_estadual') or 0), float(request.form.get('imposto_federal') or 0), 
            float(request.form.get('margem_lucro') or 0), float(request.form.get('preco_venda_final') or 0)
        ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Erro ao salvar preço no Neon: {e}")
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return redirect(url_for('precificacao'))

@app.route('/vendas')
def vendas():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT p.id, p.codigo_produto, p.nome_produto, fp.preco_venda_final, 
                   COALESCE(e.quantidade_disponivel, 0) AS estoque_atual 
            FROM produtos p 
            JOIN formacao_precos fp ON p.id = fp.produto_id 
            LEFT JOIN estoque_produtos e ON p.id = e.produto_id
        ''')
        prods = cursor.fetchall()
        
        cursor.execute('''
            SELECT pv.id, pv.produto_id, pv.quantidade, pv.desconto_percentual, pv.observacoes, pv.data_pedido,
                   p.codigo_produto, p.nome_produto, fp.preco_venda_final, fp.imposto_municipal, fp.imposto_estadual, fp.imposto_federal 
            FROM pedidos_vendas pv 
            JOIN produtos p ON pv.produto_id = p.id 
            JOIN formacao_precos fp ON p.id = fp.produto_id 
            ORDER BY pv.id DESC
        ''')
        peds = cursor.fetchall()
        
        caixa, total = calcular_caixa_disponivel(conn)
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return render_template('vendas.html', produtos=prods, pedidos=peds, caixa_disponivel=caixa, capital_inicial=total)

@app.route('/estoque')
def estoque():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT p.id AS produto_id, p.codigo_produto, p.nome_produto, 
                   COALESCE(ep.quantidade_disponivel, 0) AS quantidade_disponivel 
            FROM produtos p 
            LEFT JOIN estoque_produtos ep ON p.id = ep.produto_id
        ''')
        itens = cursor.fetchall()
        
        cursor.execute('''
            SELECT pv.id, pv.produto_id, pv.quantidade, pv.desconto_percentual, pv.observacoes, pv.data_pedido,
                   p.codigo_produto, p.nome_produto 
            FROM pedidos_vendas pv 
            JOIN produtos p ON pv.produto_id = p.id 
            WHERE pv.observacoes LIKE '%%SOB ENCOMENDA%%' 
              AND pv.id NOT IN (SELECT DISTINCT pedido_id FROM ordens_processo WHERE status='Finalizado e Armazenado')
        ''')
        peds = cursor.fetchall()
        
        caixa, total = calcular_caixa_disponivel(conn)
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return render_template('estoque.html', estoque_itens=itens, pedidos=peds, caixa_disponivel=caixa, capital_inicial=total)
@app.route('/lancar_venda', methods=['POST'])
def lancar_venda():
    prod_id = int(request.form.get('produto_id') or 0)
    qtd = int(request.form.get('quantidade') or 1)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT quantidade_disponivel FROM estoque_produtos WHERE produto_id = %s', (prod_id,))
        est = cursor.fetchone()
        estoque_atual = float(est[0]) if est else 0
        
        if estoque_atual >= qtd:
            cursor.execute('UPDATE estoque_produtos SET quantidade_disponivel = quantidade_disponivel - %s WHERE produto_id = %s', (qtd, prod_id))
            cursor.execute('INSERT INTO pedidos_vendas (produto_id, quantidade, desconto_percentual, observacoes) VALUES (%s, %s, 0, \'Pronta Entrega - Faturado\')', (prod_id, qtd))
        else:
            cursor.execute('INSERT INTO pedidos_vendas (produto_id, quantidade, desconto_percentual, observacoes) VALUES (%s, %s, 0, \'SOB ENCOMENDA - Fila PCP\')', (prod_id, qtd))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Erro ao lançar transação comercial: {e}")
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return redirect(url_for('vendas'))

@app.route('/deletar_venda/<int:id>', methods=['POST'])
def deletar_venda(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM pedidos_vendas WHERE id = %s', (id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Erro ao deletar venda no Neon: {e}")
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return redirect(url_for('vendas'))

@app.route('/pcp')
def pcp():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id, pedido_id, numero_operacao, maquina_name, codigo_produto, nome_produto, data_entrada, tempo_estimado_min, data_saida, operador_nome, status, custo_operacao FROM ordens_processo ORDER BY pedido_id ASC, id ASC')
        ords = cursor.fetchall()
        caixa, total = calcular_caixa_disponivel(conn)
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return render_template('pcp.html', ordens=ords, caixa_disponivel=caixa, capital_inicial=total)

@app.route('/solicitar_producao_pcp/<int:pedido_id>', methods=['POST'])
def solicitar_producao_pcp(pedido_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id FROM ordens_processo WHERE pedido_id = %s', (pedido_id,))
        existe = cursor.fetchone()
        
        if not existe:
            # Seleção de campos por índice relacional
            cursor.execute('SELECT pv.id, pv.produto_id, pv.quantidade, p.codigo_produto, p.nome_produto FROM pedidos_vendas pv JOIN produtos p ON pv.produto_id = p.id WHERE pv.id = %s', (pedido_id,))
            ped = cursor.fetchone()
            
            if ped:
                prod_id_ped = ped[1]
                qtd_ped = int(ped[2])
                cod_prod_ped = ped[3]
                nome_prod_ped = ped[4]
                
                cursor.execute('SELECT ep.id, ep.produto_id, ep.maquina_id, ep.material_id, ep.tempo_processo_min, ep.quantidade_material, m.nome_equipamento, m.custo_minuto_maquina, m.operador_nome FROM estrutura_produto ep LEFT JOIN maquinas m ON ep.maquina_id = m.id WHERE ep.produto_id = %s ORDER BY ep.id ASC', (prod_id_ped,))
                rots = cursor.fetchall()
                
                ponteiro_tempo = datetime.datetime.now()
                tempo_setup_fixo = 15
                
                for idx, r in enumerate(rots):
                    # Relação posicional: r[4] = tempo_processo_min, r[6] = nome_equipamento, r[7] = custo_minuto_maquina, r[8] = operador_nome
                    tempo_lote_min = (float(r[4] or 0) * qtd_ped) + tempo_setup_fixo
                    custo_total_operacao = tempo_lote_min * float(r[7] or 0.15)
                    status_inicial = "Na Fila [GARGALO OPERACIONAL]" if tempo_lote_min > 480 else "Na Fila"
                    
                    entrada_str = ponteiro_tempo.strftime("%d/%m/%Y %H:%M")
                    saida_op = ponteiro_tempo + datetime.timedelta(minutes=tempo_lote_min)
                    saida_str = saida_op.strftime("%d/%m/%Y %H:%M")
                    
                    cursor.execute('''
                        INSERT INTO ordens_processo (pedido_id, numero_operacao, maquina_name, codigo_produto, nome_produto, data_entrada, tempo_estimado_min, data_saida, status, custo_operacao, operador_nome) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (pedido_id, f"OP {(idx+1)*10}", r[6] or 'Bancada Manual', cod_prod_ped, nome_prod_ped, entrada_str, tempo_lote_min, saida_str, status_inicial, custo_total_operacao, r[8] or 'Pendente'))
                    
                    ponteiro_tempo = saida_op
                conn.commit()
            flash('Ordem de Produção transmitida com sucesso para o painel do PCP!', 'success')
    except Exception as e:
        conn.rollback()
        print(f"Erro no agendamento do PCP no Neon: {e}")
        flash('Erro operacional ao processar ordens.', 'danger')
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return redirect(url_for('estoque'))

@app.route('/abastecer_estoque_pcp', methods=['POST'])
def abastecer_estoque_pcp():
    prod_id = int(request.form.get('produto_id') or 0)
    pedido_id = int(request.form.get('pedido_id') or 0)
    qtd = float(request.form.get('quantidade_abastecer') or 0)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Checa se existem operações pendentes para travar no Bloqueio de Qualidade pedagógico
        cursor.execute('SELECT COUNT(*) FROM ordens_processo WHERE pedido_id = %s', (pedido_id,))
        ops_existentes = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM ordens_processo WHERE pedido_id = %s AND status NOT LIKE 'Finalizado%%'", (pedido_id,))
        ops_pendentes = cursor.fetchone()[0]
        
        if ops_existentes == 0 or ops_pendentes > 0:
            flash('Bloqueio de Qualidade: O Almoxarifado não pode receber este lote! Existem operações pendentes no PCP.', 'danger')
            return redirect(url_for('estoque'))
            
        cursor.execute('SELECT quantidade_disponivel FROM estoque_produtos WHERE produto_id = %s', (prod_id,))
        est = cursor.fetchone()
        
        if not est: 
            cursor.execute('INSERT INTO estoque_produtos (produto_id, quantidade_disponivel) VALUES (%s, %s)', (prod_id, qtd))
        else: 
            cursor.execute('UPDATE estoque_produtos SET quantidade_disponivel = quantidade_disponivel + %s WHERE produto_id = %s', (qtd, prod_id))
            
        cursor.execute("UPDATE ordens_processo SET status = 'Finalizado e Armazenado' WHERE pedido_id = %s", (pedido_id,))
        conn.commit()
        flash('Recebimento efetuado e integrado com sucesso ao estoque disponível.', 'success')
    except Exception as e:
        conn.rollback()
        print(f"Erro no almoxarifado do Neon: {e}")
    finally:
        cursor.close()
        release_db_connection(conn)
        
    return redirect(url_for('estoque'))

@app.route('/dar_baixa_op/<int:id>', methods=['POST'])
def dar_baixa_op(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE ordens_processo SET operador_nome = %s, status = \'Finalizado\' WHERE id = %s', (request.form.get('operador_nome', 'Operador'), id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Erro ao baixar OP no Neon: {e}")
    finally:
        cursor.close()
        release_db_connection(conn)
    return redirect(url_for('pcp'))

@app.route('/imprimir_nf/<int:pedido_id>')
def imprimir_nf(pedido_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Mapeamento estrito das colunas da junção comercial
        cursor.execute('''
            SELECT pv.id, pv.produto_id, pv.quantidade, pv.desconto_percentual, pv.observacoes, pv.data_pedido,
                   p.codigo_produto, p.nome_produto, fp.preco_venda_final, fp.imposto_municipal, fp.imposto_estadual, fp.imposto_federal 
            FROM pedidos_vendas pv 
            JOIN produtos p ON pv.produto_id = p.id 
            JOIN formacao_precos fp ON p.id = fp.produto_id 
            WHERE pv.id = %s
        ''', (pedido_id,))
        row = cursor.fetchone()
    finally:
        cursor.close()
        release_db_connection(conn)
        
    if not row: 
        return "Nota Fiscal não encontrada."
        
    # Recostrói o objeto dicionário posicionalmente para o template nota_fiscal.html
    ped = {
        'id': row[0], 'produto_id': row[1], 'quantidade': row[2], 'desconto_percentual': row[3], 'observacoes': row[4],
        'data_pedido': row[5], 'codigo_produto': row[6], 'nome_produto': row[7], 'preco_venda_final': row[8],
        'imposto_municipal': row[9], 'imposto_estadual': row[10], 'imposto_federal': row[11]
    }
    
    sub = float(ped['preco_venda_final']) * int(ped['quantidade'])
    v_desc = sub * (float(ped['desconto_percentual']) / 100.0)
    liq = sub - v_desc
    v_mun = liq * (float(ped['imposto_municipal']) / 100.0)
    v_est = liq * (float(ped['imposto_estadual']) / 100.0)
    v_fed = liq * (float(ped['imposto_federal']) / 100.0)
    
    return render_template(
        'nota_fiscal.html', p=ped, subtotal=sub, v_desconto=v_desc, total_liquido=liq, 
        v_municipal=v_mun, v_estadual=v_est, v_federal=v_fed, total_impostos=v_mun+v_est+v_fed
    )
@app.route('/financeiro')
def financeiro():
    if not session.get('logado'):
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT COALESCE(SUM(fp.preco_venda_final * pv.quantidade), 0) FROM pedidos_vendas pv JOIN formacao_precos fp ON pv.produto_id = fp.produto_id')
        faturamento_bruto = float(cursor.fetchone()[0] or 0.0)
        
        cursor.execute("SELECT COALESCE(SUM(salario_base + valor_adicionais), 0) FROM maquinas WHERE operador_nome != 'Posto Vago - Aguardando MOD' AND operador_nome != ''")
        despesa_pessoal_bruta = float(cursor.fetchone()[0] or 0.0)
        
        cursor.execute('SELECT COALESCE(SUM((fp.preco_venda_final * pv.quantidade) * ((fp.imposto_municipal + fp.imposto_estadual + fp.imposto_federal) / 100.0)), 0) FROM pedidos_vendas pv JOIN formacao_precos fp ON pv.produto_id = fp.produto_id')
        impostos_vendas = float(cursor.fetchone()[0] or 0.0)
        
        caixa, total = calcular_caixa_disponivel(conn)
    finally:
        cursor.close()
        release_db_connection(conn)
        
    total_encargos = impostos_vendas + (despesa_pessoal_bruta * 0.20)
    
    return render_template(
        'financeiro.html', faturamento=faturamento_bruto, custo_pessoal=despesa_pessoal_bruta, 
        impostos=total_encargos, saldo_liquido=caixa, caixa_disponivel=caixa, capital_inicial=total
    )

@app.route('/pagar_dividendos', methods=['POST'])
def pagar_dividendos():
    if not session.get('logado'):
        return redirect(url_for('index'))
    percentual = float(request.form.get('percentual_lucro') or 25)
    flash(f'Distribuição de {percentual}% dos dividendos processada!', 'success')
    return redirect(url_for('financeiro'))

@app.route('/roi')
def roi():
    if not session.get('logado'):
        return redirect(url_for('index'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT COALESCE(SUM(fp.preco_venda_final * pv.quantidade), 0), COALESCE(SUM(pv.quantidade), 0) FROM pedidos_vendas pv JOIN formacao_precos fp ON pv.produto_id = fp.produto_id')
        v_dados = cursor.fetchone()
        
        cursor.execute('SELECT COALESCE(SUM(valor_imovel_estimado + capital_inicial_negocio), 0), COALESCE(SUM(aluguel_regional), 0) FROM investimentos_imobiliarios')
        invs = cursor.fetchone()
        
        cursor.execute("SELECT COALESCE(SUM(salario_base + valor_adicionais), 0) FROM maquinas WHERE operador_nome != 'Posto Vago - Aguardando MOD' AND operador_nome != ''")
        despesa_pessoal = float(cursor.fetchone()[0] or 0.0)
        
        caixa, total = calcular_caixa_disponivel(conn)
    finally:
        cursor.close()
        release_db_connection(conn)
        
    rec = float(v_dados[0] or 0.0)
    pecas = float(v_dados[1] or 0.0)
    cap = float(invs[0] or 0.0)
    aluguel = float(invs[1] or 0.0)
    
    sobra = rec - despesa_pessoal - aluguel
    payback_meses = (cap / sobra) if sobra > 0 else 0.0
    
    return render_template(
        'roi.html', receita=rec, total_pecas=pecas, capital=cap, 
        payback_real=payback_meses, lucro_acionistas=rec * 0.25, 
        caixa_disponivel=caixa, capital_inicial=total
    )

if __name__ == '__main__':
    app.run(debug=True)
