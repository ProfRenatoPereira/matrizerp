import os
import math
import logging
import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from whitenoise import WhiteNoise
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from psycopg2 import pool

# Configuração de logs para monitoramento em tempo real no painel do Render
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Chave de segurança para ativação das mensagens flash e controle de login
app.secret_key = os.environ.get("SECRET_KEY", "teradmas_secret_key_2026")

# Acoplamento do WhiteNoise para servir arquivos estáticos no Render de forma nativa
app.wsgi_app = WhiteNoise(app.wsgi_app, root="static/")
CATALOGO_MAQUINAS = {
    "001 - Torno CNC Industrial": {
        "nome": "Torno CNC Industrial", 
        "custo_minuto": 0.4500,
        "pot": 15.0,
        "cons": 11.2,
        "vel": "3000 RPM",
        "avan": "15000 mm/min",
        "comp": 1000,
        "diam": 500,
        "mnt": 500,
        "preco": 250000.00,
        "dep": 2083.33,
        "venda": 50000.00,
        "operador": "Operador Especializado de Torno CNC",
        "custo_op": 0.3500,
        "salario": 3500.00,
        "adic": 700.00,
        "vida": 120
    },
    "002 - Fresadora Universal": {
        "nome": "Fresadora Universal", 
        "custo_minuto": 0.3800,
        "pot": 7.5,
        "cons": 5.6,
        "vel": "1800 RPM",
        "avan": "800 mm/min",
        "comp": 800,
        "diam": 400,
        "mnt": 350,
        "preco": 120000.00,
        "dep": 1000.00,
        "venda": 24000.00,
        "operador": "Fresador Universal",
        "custo_op": 0.2800,
        "salario": 2800.00,
        "adic": 560.00,
        "vida": 120
    },
    "003 - Furadeira de Bancada": {
        "nome": "Furadeira de Bancada", 
        "custo_minuto": 0.1500,
        "pot": 1.5,
        "cons": 1.1,
        "vel": "2500 RPM",
        "avan": "Manual",
        "comp": 300,
        "diam": 150,
        "mnt": 80,
        "preco": 8000.00,
        "dep": 66.67,
        "venda": 1600.00,
        "operador": "Auxiliar de Produção",
        "custo_op": 0.1600,
        "salario": 1600.00,
        "adic": 0.00,
        "vida": 120
    },
    "004 - Retífica Cilíndrica": {
        "nome": "Retífica Cilíndrica", 
        "custo_minuto": 0.5200,
        "pot": 11.0,
        "cons": 8.2,
        "vel": "4500 RPM",
        "avan": "2000 mm/min",
        "comp": 600,
        "diam": 300,
        "mnt": 600,
        "preco": 180000.00,
        "dep": 1500.00,
        "venda": 36000.00,
        "operador": "Retificador Especializado",
        "custo_op": 0.3800,
        "salario": 3800.00,
        "adic": 760.00,
        "vida": 120
    },
    "005 - Centro de Usinagem": {
        "nome": "Centro de Usinagem", 
        "custo_minuto": 0.8500,
        "pot": 22.0,
        "cons": 16.5,
        "vel": "12000 RPM",
        "avan": "30000 mm/min",
        "comp": 1200,
        "diam": 600,
        "mnt": 1200,
        "preco": 550000.00,
        "dep": 4583.33,
        "venda": 110000.00,
        "operador": "Programador e Operador de Centro de Usinagem",
        "custo_op": 0.4800,
        "salario": 4800.00,
        "adic": 960.00,
        "vida": 120
    }
}
CATALOGO_MATERIAIS = {
    "Aço SAE 1020": {
        "cod": "MAT-ACO-1020",
        "nome": "Barra de Aço Carbono SAE 1020",
        "preco": 45.50,
        "dim": "Ø 3\" x 1000mm",
        "vol": 100.0
    },
    "Aço SAE 4140": {
        "cod": "MAT-ACO-4140",
        "nome": "Barra de Aço Aliado SAE 4140",
        "preco": 125.00,
        "dim": "Ø 2\" x 1000mm",
        "vol": 50.0
    },
    "Alumínio 6061": {
        "cod": "MAT-ALU-6061",
        "nome": "Tarugo de Alumínio Naval 6061-T6",
        "preco": 85.00,
        "dim": "Ø 4\" x 500mm",
        "vol": 80.0
    },
    "Polímero Nylon 6.6": {
        "cod": "MAT-NYLON-66",
        "nome": "Tarugo de Nylon 6.6 Técnico",
        "preco": 35.00,
        "dim": "Ø 50mm x 1000mm",
        "vol": 120.0
    }
}
DATABASE_URL = os.environ.get("DATABASE_URL")

try:
    if DATABASE_URL:
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        
        conexao_pool = pool.ThreadedConnectionPool(
            minconn=1, 
            maxconn=10, 
            dsn=DATABASE_URL,
            sslmode='require'
        )
        logger.info("Pool de conexões inicializado para o Neon PostgreSQL (Nuvem).")
    else:
        conexao_pool = pool.ThreadedConnectionPool(
            minconn=1, 
            maxconn=5, 
            dsn="dbname=matrizerp user=postgres password=postgres host=localhost"
        )
        logger.info("Pool de conexões inicializado para o PostgreSQL Local.")
except Exception as e:
    logger.critical(f"Falha crítica ao criar o Pool de conexões: {e}")
    raise e
def inicializar_banco():
    """Cria o esqueleto relacional completo no Postgres Neon de forma sequencial"""
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        # Tabela 1: Usuários e Equipes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                usuario VARCHAR(150) UNIQUE NOT NULL,
                senha VARCHAR(255) NOT NULL
            );
        ''')
        
        # Tabela 2: Investimentos Imobiliários
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS investimentos_imobiliarios (
                id SERIAL PRIMARY KEY,
                turma_nome VARCHAR(255),
                cidade_regiao VARCHAR(255),
                bairro_imovel VARCHAR(255),
                area_imovel NUMERIC(10,2),
                taxa_selic NUMERIC(5,2),
                valor_imovel_estimado NUMERIC(12,2),
                aluguel_regional NUMERIC(12,2),
                perc_acionistas NUMERIC(5,2),
                capital_inicial_negocio NUMERIC(15,2)
            );
        ''')

        # Tabela 3: Máquinas e Equipamentos
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
                horas_trabalhadas INTEGER DEFAULT 0,
                preco_compra NUMERIC(12,2),
                depreciacao_mensal NUMERIC(10,2),
                valor_venda_final NUMERIC(12,2),
                custo_minuto_maquina NUMERIC(10,4),
                operador_nome VARCHAR(255),
                custo_minuto_operador NUMERIC(10,4),
                salario_base NUMERIC(10,2),
                valor_adicionais NUMERIC(10,2),
                turno_trabalho VARCHAR(100) DEFAULT 'Diurno',
                dia_semana VARCHAR(100) DEFAULT 'Regular',
                vida_util_meses INTEGER
            );
        ''')

        # Tabela 4: Materiais e Almoxarifado
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS materiais (
                id SERIAL PRIMARY KEY,
                codigo_material VARCHAR(100) UNIQUE NOT NULL,
                nome_material VARCHAR(255) NOT NULL,
                preco_unidade NUMERIC(10,2),
                dimensoes VARCHAR(100),
                volume_disponivel NUMERIC(10,2)
            );
        ''')

        # Tabela 5: Engenharia de Produtos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS produtos (
                id SERIAL PRIMARY KEY,
                codigo_produto VARCHAR(100) UNIQUE NOT NULL,
                nome_produto VARCHAR(255) NOT NULL,
                custo_total_fabricacao NUMERIC(10,2) DEFAULT 0.0
            );
        ''')
        
        # Continua na próxima parte para manter a segurança do buffer...
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro na criação inicial das tabelas: {e}")
        raise e
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
def complementar_tabelas():
    """Cria tabelas dependentes e chaves estrangeiras necessárias para o fluxo"""
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        # Tabela 6: Roteiro e Estrutura do Produto (BOM)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS estrutura_produto (
                id SERIAL PRIMARY KEY,
                produto_id INTEGER REFERENCES produtos(id) ON DELETE CASCADE,
                maquina_id INTEGER REFERENCES maquinas(id) ON DELETE SET NULL,
                material_id INTEGER REFERENCES materiais(id) ON DELETE SET NULL,
                tempo_processo_min NUMERIC(10,2),
                quantidade_material NUMERIC(10,2)
            );
        ''')

        # Tabela 7: Formação de Preço Estratégica
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS formacao_precos (
                id SERIAL PRIMARY KEY,
                produto_id INTEGER UNIQUE REFERENCES produtos(id) ON DELETE CASCADE,
                imposto_municipal NUMERIC(5,2),
                imposto_estadual NUMERIC(5,2),
                imposto_federal NUMERIC(5,2),
                margem_lucro NUMERIC(5,2),
                preco_venda_final NUMERIC(10,2)
            );
        ''')

        # Tabela 8: Carteira de Pedidos de Vendas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pedidos_vendas (
                id SERIAL PRIMARY KEY,
                produto_id INTEGER REFERENCES produtos(id) ON DELETE CASCADE,
                quantidade INTEGER NOT NULL,
                desconto_percentual NUMERIC(5,2) DEFAULT 0.0,
                observacoes VARCHAR(255),
                data_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        # Tabela 9: Ordens de Processo e Operações (PCP)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ordens_processo (
                id SERIAL PRIMARY KEY,
                pedido_id INTEGER REFERENCES pedidos_vendas(id) ON DELETE CASCADE,
                numero_operacao VARCHAR(50),
                maquina_name VARCHAR(255),
                codigo_produto VARCHAR(100),
                nome_produto VARCHAR(255),
                data_entrada VARCHAR(100),
                tempo_estimado_min NUMERIC(10,2),
                data_saida VARCHAR(100),
                operador_nome VARCHAR(255),
                status VARCHAR(100),
                custo_operacao NUMERIC(10,2)
            );
        ''')

        # Tabela 10: Estoque Físico de Produtos Acabados
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS estoque_produtos (
                id SERIAL PRIMARY KEY,
                produto_id INTEGER UNIQUE REFERENCES produtos(id) ON DELETE CASCADE,
                quantidade_disponivel NUMERIC(10,2) DEFAULT 0.0
            );
        ''')

        # Tabela 11: Requisições e Compras de Ativos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS requisicoes_compras (
                id SERIAL PRIMARY KEY,
                equipamento_tipo VARCHAR(255),
                especificacao_desejada VARCHAR(255),
                quantidade INTEGER,
                status VARCHAR(100) DEFAULT 'Aguardando Cotação',
                preco_cotado NUMERIC(12,2) DEFAULT 0.0,
                potencia_cotada NUMERIC(10,2) DEFAULT 0.0,
                depreciacao_sugerida NUMERIC(10,2) DEFAULT 0.0,
                vida_util_sugerida INTEGER DEFAULT 120,
                data_requisicao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro na complementação estrutural das tabelas: {e}")
        raise e
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
def popular_dados_iniciais():
    """Insere os dados pedagógicos padrão caso as tabelas estejam vazias"""
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM usuarios;")
        if cursor.fetchone()[0] == 0:
            senha_admin = generate_password_hash("admin123")
            cursor.execute("INSERT INTO usuarios (usuario, senha) VALUES (%s, %s);", ("admin", senha_admin))
            
        cursor.execute("SELECT COUNT(*) FROM maquinas;")
        if cursor.fetchone()[0] == 0:
            for k, m in CATALOGO_MAQUINAS.items():
                if k in ['001 - Torno CNC Industrial', '002 - Fresadora Universal', '003 - Furadeira de Bancada']:
                    minutos_mes = 44 * 4.33 * 60
                    c_mm = (m['dep'] / minutos_mes) + ((m['pot'] * 0.75) / 60) + (13500.00 / minutos_mes)
                    
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
                    
        cursor.execute("SELECT COUNT(*) FROM materiais;")
        if cursor.fetchone()[0] == 0:
            for mat in CATALOGO_MATERIAIS.values():
                cursor.execute("""
                    INSERT INTO materiais (codigo_material, nome_material, preco_unidade, dimensoes, volume_disponivel) 
                    VALUES (%s, %s, %s, %s, %s)
                """, (mat['cod'], mat['nome'], mat['preco'], mat['dim'], mat['vol']))
                
        cursor.execute("SELECT COUNT(*) FROM produtos;")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO produtos (id, codigo_produto, nome_produto, custo_total_fabricacao) VALUES (1, 'PROD-EIXO-CNC', 'Eixo de Transmissão Usinado', 115.40)")
            cursor.execute("INSERT INTO estrutura_produto (produto_id, maquina_id, material_id, tempo_processo_min, quantidade_material) VALUES (1, 1, 2, 12.0, 1.5)")
            cursor.execute("INSERT INTO formacao_precos (produto_id, imposto_municipal, imposto_estadual, imposto_federal, margem_lucro, preco_venda_final) VALUES (1, 5.0, 18.0, 9.25, 35.0, 245.50)")
            cursor.execute("INSERT INTO estoque_produtos (produto_id, quantidade_disponivel) VALUES (1, 25.0)")
            
        conn.commit()
        logger.info("Povoamento do banco de dados concluído com sucesso.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao popular dados iniciais: {e}")
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
def calcular_caixa_disponivel(conn):
    """Realiza a consolidação contábil serverless de ativos e despesas da equipe"""
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT capital_inicial_negocio, aluguel_regional FROM investimentos_imobiliarios ORDER BY id DESC LIMIT 1')
        ult_imovel = cursor.fetchone()
        if not ult_imovel: 
            return 0.0, 0.0
            
        capital_inicial = float(ult_imovel[0] or 0.0)
        aluguel_fixo = float(ult_imovel[1] or 0.0)
        
        cursor.execute('SELECT COALESCE(SUM(preco_compra), 0) FROM maquinas')
        investido_maquinas = float(cursor.fetchone()[0] or 0.0)
        
        cursor.execute('SELECT COALESCE(SUM(preco_unidade * volume_disponivel), 0) FROM materiais')
        comprado_materiais = float(cursor.fetchone()[0] or 0.0)
        
        cursor.execute('SELECT COALESCE(SUM(fp.preco_venda_final * pv.quantidade), 0) FROM pedidos_vendas pv JOIN formacao_precos fp ON pv.produto_id = fp.produto_id')
        faturamento = float(cursor.fetchone()[0] or 0.0)
        
        cursor.execute("SELECT COALESCE(SUM(salario_base + valor_adicionais), 0) FROM maquinas WHERE operador_nome != 'Posto Vago - Aguardando MOD' AND operador_nome != ''")
        folha_rh = float(cursor.fetchone()[0] or 0.0)
        
        caixa_atual = capital_inicial - investido_maquinas - comprado_materiais + faturamento - folha_rh - aluguel_fixo
        return caixa_atual, capital_inicial
    except Exception as e:
        logger.error(f"Erro ao calcular fluxo de caixa: {e}")
        return 0.0, 0.0
    finally:
        cursor.close()
@app.route('/')
def index():
    """Renderiza a tela de login inicial do sistema ERP"""
    return render_template('login.html')

@app.route('/login_validar', methods=['POST'])
def login_validar():
    """Valida as credenciais criptografadas inseridas pela equipe de alunos"""
    user_input = request.form.get('username')
    pass_input = request.form.get('password')
    
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id, usuario, senha FROM usuarios WHERE usuario = %s', (user_input,))
        user = cursor.fetchone()
        
        if user and check_password_hash(user[2], pass_input):
            session['logado'] = True
            session['usuario_equipe'] = user_input
            flash('Acesso concedido com sucesso!', 'success')
            return redirect(url_for('estrutura'))
        else:
            flash('Usuário ou senha inválidos.', 'danger')
    except Exception as e:
        logger.error(f"Erro na validação de login: {e}")
        flash('Erro operacional ao processar o login.', 'danger')
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
        
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    """Limpa a sessão ativa e desconecta o usuário com segurança"""
    session.clear()
    flash('Desconectado com sucesso.', 'success')
    return redirect(url_for('index'))
@app.route('/professor_painel_secreto')
def professor_painel():
    """Exibe a central de controle pedagógico para gerenciamento de equipes"""
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id, usuario FROM usuarios ORDER BY usuario ASC')
        todas_equipes = cursor.fetchall()
    except Exception as e:
        logger.error(f"Erro ao carregar painel do professor: {e}")
        todas_equipes = []
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
        
    return render_template('professor.html', usuarios=todas_equipes)

@app.route('/professor/cadastrar', methods=['POST'])
def professor_cadastrar():
    """Permite ao docente criar novas credenciais de acesso para grupos de alunos"""
    novo_user = request.form.get('novo_user').strip().lower().replace(" ", "")
    senha_inicial = request.form.get('senha_inicial')
    hash_senha = generate_password_hash(senha_inicial)
    
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO os_usuarios (usuario, senha) VALUES (%s, %s)', (novo_user, hash_senha))
        conn.commit()
        flash(f"Equipe '{novo_user}' registrada com sucesso!", 'success')
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        flash("Erro: Essa equipe já está cadastrada.", 'danger')
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro no cadastro de nova equipe: {e}")
        flash(f"Erro inesperado ao registrar equipe: {e}", 'danger')
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
        
    return redirect(url_for('professor_painel'))

@app.route('/professor/resetar', methods=['POST'])
def professor_resetar():
    """Força a alteração de senhas das equipes através do painel master"""
    user_aluno = request.form.get('username')
    nova_senha = request.form.get('nova_senha')
    novo_hash = generate_password_hash(nova_senha)
    
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE usuarios SET senha = %s WHERE usuario = %s', (novo_hash, user_aluno))
        conn.commit()
        flash(f"Sucesso! A senha da equipe '{user_aluno}' foi alterada para '{nova_senha}'.", 'success')
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao resetar senha da equipe {user_aluno}: {e}")
        flash(f"Erro ao resetar senha: {e}", 'danger')
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
        
    return redirect(url_for('professor_painel'))
@app.route('/inicializar_simulador', methods=['POST'])
def inicializar_simulador():
    """Limpa completamente a base operacional da equipe para um novo cenário pedagógico"""
    if not session.get('logado'):
        return redirect(url_for('index'))
        
    nome_empresa = request.form.get('nome_empresa', 'Empresa Simulada S/A')
    try: 
        capital_inicial = float(request.form.get('capital_inicial', 0))
    except ValueError: 
        capital_inicial = 0.0
        
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        # Executa o truncate em cascata limpando dependências industriais e comerciais
        cursor.execute('''
            TRUNCATE TABLE investimentos_imobiliarios, maquinas, materiais, produtos, 
            estrutura_produto, formacao_precos, estoque_produtos, pedidos_vendas, 
            ordens_processo, requisicoes_compras RESTART IDENTITY CASCADE;
        ''')
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao executar truncate de limpeza no Neon: {e}")
        flash(f"Erro ao limpar tabelas no Neon: {e}", 'danger')
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
        
    # Reconstrói a integridade relacional padrão
    inicializar_banco()
    complementar_tabelas()
    
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO investimentos_imobiliarios (
                turma_nome, cidade_regiao, bairro_imovel, area_imovel, taxa_selic, 
                valor_imovel_estimado, aluguel_regional, perc_acionistas, capital_inicial_negocio
            ) VALUES (%s, 'Não Definido', 'Não Definido', 0.0, 11.39, 0.0, 0.0, 0.0, %s);
        ''', (nome_empresa, capital_inicial))
        conn.commit()
        flash(f'Empresa {nome_empresa} inicializada com sucesso!', 'success')
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao inserir cenário básico de simulação: {e}")
        flash(f"Erro ao inserir cenário básico de simulação: {e}", 'danger')
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
        
    return redirect(url_for('estrutura'))

@app.route('/estrutura')
def estrutura():
    """Central de investimentos estruturais e dados imobiliários"""
    if not session.get('logado'):
        return redirect(url_for('index'))
        
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT id, turma_nome, cidade_regiao, bairro_imovel, area_imovel, taxa_selic, 
                   valor_imovel_estimado, aluguel_regional, perc_acionistas, capital_inicial_negocio 
            FROM investimentos_imobiliarios ORDER BY id DESC;
        ''')
        registros = cursor.fetchall()
        caixa, total = calcular_caixa_disponivel(conn)
    except Exception as e:
        logger.error(f"Erro ao carregar estrutura imobiliária: {e}")
        registros = []
        caixa, total = 0.0, 0.0
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
        
    return render_template('estrutura.html', taxa_atual=11.39, registros=registros, caixa_disponivel=caixa, capital_inicial=total)
@app.route('/salvar_estrutura', methods=['POST'])
def salvar_estrutura():
    """Registra novos dados locatícios e investimentos imobiliários"""
    if not session.get('logado'):
        return redirect(url_for('index'))
        
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT capital_inicial_negocio FROM investimentos_imobiliarios ORDER BY id DESC LIMIT 1;')
        ultimo_registro = cursor.fetchone()
        capital_fixado = float(ultimo_registro[0]) if ultimo_registro else 0.0
        
        cursor.execute('''
            INSERT INTO investimentos_imobiliarios (
                turma_nome, cidade_regiao, bairro_imovel, area_imovel, taxa_selic, 
                valor_imovel_estimado, aluguel_regional, perc_acionistas, capital_inicial_negocio
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
        ''', (
            request.form.get('turma_nome', 'Grupo Geral'), request.form.get('cidade_regiao', 'Curitiba'), 
            request.form.get('bairro_imovel', 'Centro'), float(request.form.get('area_imovel') or 0), 
            float(request.form.get('taxa_selic') or 11.39), float(request.form.get('valor_imovel_estimado') or 0), 
            float(request.form.get('aluguel_regional') or 0), float(request.form.get('perc_acionistas') or 0), 
            capital_fixado
        ))
        conn.commit()
        flash('Estrutura de investimentos da planta calibrada com sucesso!', 'success')
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao salvar estrutura imobiliária no Neon: {e}")
        flash('Erro operacional ao salvar alterações imobiliárias.', 'danger')
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
        
    return redirect(url_for('estrutura'))

@app.route('/alterar_estrutura/<int:id>', methods=['POST'])
def alterar_estrutura(id):
    """Atualiza as propriedades locatícias ou tributárias de uma planta ativa"""
    if not session.get('logado'):
        return redirect(url_for('index'))
        
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT capital_inicial_negocio FROM investimentos_imobiliarios WHERE id = %s;', (id,))
        ultimo_registro = cursor.fetchone()
        capital_fixado = float(ultimo_registro[0]) if ultimo_registro else 0.0
        
        cursor.execute('''
            UPDATE investimentos_imobiliarios 
            SET turma_nome=%s, cidade_regiao=%s, bairro_imovel=%s, area_imovel=%s, taxa_selic=%s, 
                valor_imovel_estimado=%s, aluguel_regional=%s, perc_acionistas=%s, capital_inicial_negocio=%s 
            WHERE id=%s;
        ''', (
            request.form.get('turma_nome', 'Grupo Geral'), request.form.get('cidade_regiao', 'Curitiba'), 
            request.form.get('bairro_imovel', 'Centro'), float(request.form.get('area_imovel') or 0), 
            float(request.form.get('taxa_selic') or 11.39), float(request.form.get('valor_imovel_estimado') or 0), 
            float(request.form.get('aluguel_regional') or 0), float(request.form.get('perc_acionistas') or 0), 
            capital_fixado, id
        ))
        conn.commit()
        flash('Registro de infraestrutura atualizado na nuvem!', 'success')
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao alterar estrutura no Neon: {e}")
        flash('Falha ao atualizar parâmetros de infraestrutura.', 'danger')
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
        
    return redirect(url_for('estrutura'))

@app.route('/deletar_estrutura/<int:id>', methods=['POST'])
def deletar_estrutura(id):
    """Remove uma parametrização de infraestrutura do histórico"""
    if not session.get('logado'):
        return redirect(url_for('index'))
        
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM investimentos_imobiliarios WHERE id = %s;', (id,))
        conn.commit()
        flash('Registro de infraestrutura removido!', 'success')
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao deletar estrutura no Neon: {e}")
        flash('Não foi possível remover este registro.', 'danger')
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
        
    return redirect(url_for('estrutura'))
@app.route('/maquinas')
def maquinas():
    """Gera a listagem e o gerenciamento de máquinas e equipamentos ativos"""
    if not session.get('logado'):
        return redirect(url_for('index'))
    
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        # Busca todas as máquinas registradas na tabela do banco de dados
        cursor.execute('''
            SELECT id, nome_equipamento, potencia, consumo_eletrico, velocidade, 
                   avanco, preco_compra, depreciacao_mensal, custo_minuto_maquina, operador_nome 
            FROM maquinas 
            ORDER BY id ASC;
        ''')
        lista_maquinas = cursor.fetchall()
        
        # Puxa o fluxo de caixa consolidado para exibir no topo da página
        caixa, total = calcular_caixa_disponivel(conn)
    except Exception as e:
        logger.error(f"Erro ao carregar painel de maquinas: {e}")
        lista_maquinas = []
        caixa, total = 0.0, 0.0
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
        
    # Renderiza o arquivo HTML correspondente passando as variáveis necessárias
    return render_template('maquinas.html', maquinas=lista_maquinas, caixa_disponivel=caixa, capital_inicial=total)

@app.route('/rh')
def rh():
    """Gera a listagem de mão de obra direta e indireta vinculada aos ativos"""
    if not session.get('logado'):
        return redirect(url_for('index'))
        
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT id, nome_equipamento, operador_nome, salario_base, valor_adicionais, turno_trabalho, dia_semana 
            FROM maquinas 
            WHERE operador_nome != 'Posto Vago - Aguardando MOD' AND operador_nome != '';
        ''')
        colaboradores = cursor.fetchall()
        caixa, total = calcular_caixa_disponivel(conn)
    except Exception as e:
        logger.error(f"Erro ao carregar colaboradores do RH: {e}")
        colaboradores = []
        caixa, total = 0.0, 0.0
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
        
    return render_template('rh.html', colaboradores=colaboradores, caixa_disponivel=caixa, capital_inicial=total)

@app.route('/salvar_colaborador', methods=['POST'])
def salvar_colaborador():
    """Aloca Mão de Obra Direta em postos produtivos vagos ou cria postos de apoio"""
    if not session.get('logado'):
        return redirect(url_for('index'))
        
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM maquinas WHERE operador_nome = 'Posto Vago - Aguardando MOD' LIMIT 1;")
        posto_vago = cursor.fetchone()
        
        if posto_vago:
            posto_id = posto_vago[0]
            cursor.execute('''
                UPDATE maquinas 
                SET operador_nome = %s, salario_base = %s, valor_adicionais = %s, 
                    turno_trabalho = %s, dia_semana = %s, custo_minuto_operador = %s 
                WHERE id = %s;
            ''', (
                request.form.get('nome_completo', 'Colaborador'), float(request.form.get('salario_base') or 0), 
                float(request.form.get('valor_adicionais') or 0), request.form.get('turno', 'Diurno'), 
                request.form.get('dia_semana', 'Regular'), float(request.form.get('custo_minuto_operador') or 0), 
                posto_id
            ))
            conn.commit()
            flash('Mão de Obra Direta (MOD) alocada com sucesso no maquinário ativo!', 'success')
        else:
            cursor.execute('''
                INSERT INTO maquinas (
                    nome_equipamento, potencia, consumo_eletrico, velocidade, avanco, comprimento_max, 
                    diametro_max, frequencia_manutencao, horas_trabalhadas, preco_compra, depreciacao_mensal, 
                    valor_venda_final, custo_minuto_maquina, operador_nome, custo_minuto_operador, salario_base, 
                    valor_adicionais, turno_trabalho, dia_semana, vida_util_meses
                ) VALUES (
                    'Posto de Apoio / Indireto', 0, 0, 'N/A', 'N/A', 0, 0, 9999, 0, 0, 0, 0, 0, %s, %s, %s, %s, %s, %s, 120
                );
            ''', (
                request.form.get('nome_completo', 'Colaborador'), float(request.form.get('custo_minuto_operador') or 0), 
                float(request.form.get('salario_base') or 0), float(request.form.get('valor_adicionais') or 0), 
                request.form.get('turno', 'Diurno'), request.form.get('dia_semana', 'Regular')
            ))
            conn.commit()
            flash('Mão de Obra Indireta (MOI) registrada com sucesso na central de RH.', 'success')
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao processar folha e alocação de RH no Neon: {e}")
        flash(f"Erro ao alocar folha de RH no Neon: {e}", 'danger')
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
        
    return redirect(url_for('rh'))
@app.route('/imprimir_holerite/<int:id>/<string:tipo>')
def imprimir_holerite(id, tipo):
    """Gera o holerite completo com os cálculos tributários aplicados"""
    if not session.get('logado'):
        return redirect(url_for('index'))
        
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id, operador_nome, salario_base, valor_adicionais, dia_semana, turno_trabalho FROM maquinas WHERE id = %s', (id,))
        col = cursor.fetchone()
    except Exception as e:
        logger.error(f"Erro ao buscar dados para impressão do holerite: {e}")
        col = None
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
        
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
    
    if total_proventos <= 1518.00:
        inss = total_proventos * 0.075
    elif total_proventos <= 2793.88:
        inss = (total_proventos * 0.09) - 22.77
    elif total_proventos <= 4190.83:
        inss = (total_proventos * 0.12) - 106.59
    elif total_proventos <= 8157.41:
        inss = (total_proventos * 0.14) - 190.40
    else:
        inss = 951.64

    base_irrf = total_proventos - inss
    
    if base_irrf <= 2259.20:
        irrf = 0.0
    elif base_irrf <= 2826.65:
        irrf = (base_irrf * 0.075) - 169.44
    elif base_irrf <= 3751.05:
        irrf = (base_irrf * 0.15) - 381.44
    elif base_irrf <= 4664.68:
        irrf = (base_irrf * 0.225) - 662.77
    else:
        irrf = (base_irrf * 0.275) - 896.00
    
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
    """Gera o painel de estimativas comerciais e engenharia reversa de preços"""
    if not session.get('logado'):
        return redirect(url_for('index'))
        
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id, nome_equipamento, custo_minuto_maquina FROM maquinas')
        maqs = cursor.fetchall()
        caixa, total = calcular_caixa_disponivel(conn)
    except Exception as e:
        logger.error(f"Erro ao carregar orçamentos: {e}")
        maqs = []
        caixa, total = 0.0, 0.0
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
        
    return render_template('orcamentos.html', maquinas=maqs, caixa_disponivel=caixa, capital_inicial=total)

@app.route('/salvar_orcamento_calculado', methods=['POST'])
def salvar_orcamento_calculado():
    """Salva o orçamento como produto e injeta direto na carteira de vendas como pedido"""
    if not session.get('logado'):
        return redirect(url_for('index'))
        
    tipo = request.form.get('tipo_produto')
    nome_item = request.form.get('nome_item')
    lote = int(request.form.get('lote') or 1)
    preco_final = float(request.form.get('preco_final_calculado') or 0.0)
    sku = f"ORC-{tipo.upper()}-{int(preco_final)%1000}"
    
    conn = conexao_pool.getconn()
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
        logger.error(f'Erro operacional ao salvar orçamento calculado no Neon: {e}')
        flash(f'Erro operacional no Neon: {e}', 'danger')
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
        
    return redirect(url_for('vendas'))
@app.route('/requisicoes')
def requisicoes():
    """Exibe o painel de requisições enviadas e andamento das cotações"""
    if not session.get('logado'):
        return redirect(url_for('index'))
        
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id, equipamento_tipo, especificacao_desejada, quantidade, status, preco_cotado, potencia_cotada, depreciacao_sugerida, vida_util_sugerida, data_requisicao FROM requisicoes_compras ORDER BY id DESC')
        reqs = cursor.fetchall()
        caixa, total = calcular_caixa_disponivel(conn)
    except Exception as e:
        logger.error(f"Erro ao carregar requisições: {e}")
        reqs = []
        caixa, total = 0.0, 0.0
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
        
    return render_template('requisicoes.html', requisicoes=reqs, caixa_disponivel=caixa, capital_inicial=total)

@app.route('/compras')
def compras():
    """Central de aprovação e efetivação de compras cotadas"""
    if not session.get('logado'):
        return redirect(url_for('index'))
        
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, equipamento_tipo, especificacao_desejada, quantidade, status, preco_cotado, potencia_cotada, depreciacao_sugerida, vida_util_sugerida, data_requisicao FROM requisicoes_compras WHERE status LIKE 'Cotado%%' ORDER BY id DESC")
        cotadas = cursor.fetchall()
        caixa, total = calcular_caixa_disponivel(conn)
    except Exception as e:
        logger.error(f"Erro ao carregar compras: {e}")
        cotadas = []
        caixa, total = 0.0, 0.0
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
        
    return render_template('compras.html', requisicoes_cotadas=cotadas, caixa_disponivel=caixa, capital_inicial=total)

@app.route('/salvar_requisicao', methods=['POST'])
def salvar_requisicao():
    """Cria uma nova linha de demanda para o departamento de suprimentos"""
    if not session.get('logado'):
        return redirect(url_for('index'))
        
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO requisicoes_compras (equipamento_tipo, especificacao_desejada, quantidade) VALUES (%s, %s, %s)', (request.form.get('equipamento_tipo', 'Equipamento'), request.form.get('especificacao_desejada', 'N/A'), int(request.form.get('quantidade') or 1)))
        conn.commit()
        flash('Requisição enviada com sucesso para o departamento de compras!', 'success')
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao salvar requisição: {e}")
        flash('Erro ao registrar a requisição no sistema.', 'danger')
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
        
    return redirect(url_for('requisicoes'))
@app.route('/cotar_internet/<int:id>', methods=['POST'])
def cotar_internet(id):
    """Simula uma varredura web com inteligência pedagógica para calibrar preços e potências do ativo"""
    if not session.get('logado'):
        return redirect(url_for('index'))
        
    conn = conexao_pool.getconn()
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
            flash('Cotação de mercado calibrada e atualizada com sucesso via robô!', 'success')
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao cotar internet: {e}")
        flash('Falha ao processar cotação de mercado automatizada.', 'danger')
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
        
    return redirect(url_for('requisicoes'))
@app.route('/efetivar_compra/<int:id>', methods=['POST'])
def efetivar_compra(id):
    """Garante a transação de compra, reduz o caixa e integra o bem de capital à planta ou almoxarifado"""
    if not session.get('logado'):
        return redirect(url_for('index'))
        
    conn = conexao_pool.getconn()
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
                cursor.execute('''
                    INSERT INTO materiais (codigo_material, nome_material, preco_unidade, dimensoes, volume_disponivel) 
                    VALUES (%s, %s, %s, 'Lote', %s)
                    ON CONFLICT (codigo_material) 
                    DO UPDATE SET nome_material = EXCLUDED.nome_material, preco_unidade = EXCLUDED.preco_unidade, volume_disponivel = EXCLUDED.volume_disponivel;
                ''', (sku_gerado, req[1], preco / float(req[2]), float(req[2])))
                
            cursor.execute("UPDATE requisicoes_compras SET status = 'Comprado e Ativado' WHERE id = %s", (id,))
            conn.commit()
            flash('Compra realizada! Os ativos foram provisionados e incorporados à planta com sucesso.', 'success')
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao efetivar compra: {e}")
        flash('Erro operacional ao processar faturamento e ativação da compra.', 'danger')
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
        
    return redirect(url_for('requisicoes'))

@app.route('/deletar_requisicao/<int:id>', methods=['POST'])
def deletar_requisicao(id):
    """Cancela e descarta um registro de intenção de compra da lista"""
    if not session.get('logado'):
        return redirect(url_for('index'))
        
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM requisicoes_compras WHERE id = %s', (id,))
        conn.commit()
        flash('Requisição de compra cancelada e arquivada!', 'success')
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao deletar requisição: {e}")
        flash('Erro ao tentar expurgar a requisição de compra.', 'danger')
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
        
    return redirect(url_for('requisicoes'))
@app.route('/inventario')
@app.route('/materiais')
def materiais():
    """Gera a visualização consolidada do almoxarifado (Insumos e Produtos Acabados)"""
    if not session.get('logado'):
        return redirect(url_for('index'))
        
    conn = conexao_pool.getconn()
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
    except Exception as e:
        logger.error(f"Erro ao carregar inventário de materiais: {e}")
        mats = []
        itens_acabados = []
        caixa, total = 0.0, 0.0
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
        
    return render_template('materiais.html', materiais=mats, estoque_itens=itens_acabados, caixa_disponivel=caixa, capital_inicial=total)

@app.route('/salvar_material', methods=['POST'])
def salvar_material():
    """Registra uma nova matéria-prima ou componente básico no estoque"""
    if not session.get('logado'):
        return redirect(url_for('index'))
        
    conn = conexao_pool.getconn()
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
        flash('Material cadastrado com sucesso!', 'success')
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        logger.error("Tentativa de cadastro com SKU duplicado na tabela de materiais.")
        flash('Erro: SKU duplicado!', 'danger')
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro operacional ao salvar material no Neon: {e}")
        flash(f"Erro operacional no Neon: {e}", 'danger')
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
        
    return redirect(url_for('materiais'))

@app.route('/alterar_material/<int:id>', methods=['POST'])
def alterar_material(id):
    """Modifica parâmetros ou volumes físicos de matérias-primas"""
    if not session.get('logado'):
        return redirect(url_for('index'))
        
    conn = conexao_pool.getconn()
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
        flash('Material atualizado com sucesso!', 'success')
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao alterar material no Neon: {e}")
        flash('Erro ao atualizar as especificações do material.', 'danger')
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
        
    return redirect(url_for('materiais'))

@app.route('/deletar_material/<int:id>', methods=['POST'])
def deletar_material(id):
    """Remove definitivamente um insumo do almoxarifado"""
    if not session.get('logado'):
        return redirect(url_for('index'))
        
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM materiais WHERE id = %s', (id,))
        conn.commit()
        flash('Material removido do inventário!', 'success')
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao deletar material no Neon: {e}")
        flash('Erro ao remover o material selecionado.', 'danger')
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
        
    return redirect(url_for('materiais'))
# ==============================================================================
# PARTE 20 DE 23: MÓDULO DE ENGENHARIA (BOM) E LISTA DE MATERIAIS
# ==============================================================================

@app.route('/engenharia')
def engenharia():
    """Gera a árvore de estrutura de produtos (BOM) e roteiros de fabricação"""
    if not session.get('logado'):
        return redirect(url_for('index'))
    conn = conexao_pool.getconn()
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
    except Exception as e:
        logger.error(f"Erro ao carregar módulo de engenharia: {e}")
        prods, maqs, mats, comps = [], [], [], []
        caixa, total = 0.0, 0.0
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
    return render_template('engenharia.html', produtos=prods, maquinas=maqs, materiais=mats, composicoes=comps, caixa_disponivel=caixa, capital_inicial=total)

@app.route('/salvar_produto', methods=['POST'])
def salvar_produto():
    """Cadastra um novo produto acabado na árvore de engenharia"""
    if not session.get('logado'):
        return redirect(url_for('index'))
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO produtos (codigo_produto, nome_produto) VALUES (%s, %s)', (request.form.get('codigo_produto', 'PROD').strip(), request.form.get('nome_produto', 'Acabado').strip()))
        conn.commit()
        flash('Produto de engenharia cadastrado com sucesso!', 'success')
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        flash('Erro: Produto duplicado.', 'danger')
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro operacional ao salvar produto no Neon: {e}")
        flash(f"Erro operacional no Neon: {e}", 'danger')
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
    return redirect(url_for('engenharia'))

@app.route('/vincular_estrutura', methods=['POST'])
def vincular_estrutura():
    """Vincula uma máquina e um insumo à árvore de processos do item (BOM)"""
    if not session.get('logado'):
        return redirect(url_for('index'))
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    m_id = int(request.form.get('maquina_id')) if request.form.get('maquina_id') and request.form.get('maquina_id').isdigit() else None
    mat_id = int(request.form.get('material_id')) if request.form.get('material_id') and request.form.get('material_id').isdigit() else None
    try:
        cursor.execute('''
            INSERT INTO estrutura_produto (produto_id, maquina_id, material_id, tempo_processo_min, quantidade_material) 
            VALUES (%s, %s, %s, %s, %s)
        ''', (int(request.form.get('produto_id') or 0), m_id, mat_id, float(request.form.get('tempo_processo_min') or 0), float(request.form.get('quantidade_material') or 0)))
        conn.commit()
        flash('Estrutura vinculada com sucesso ao item de engenharia!', 'success')
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao vincular estrutura de engenharia no Neon: {e}")
        flash('Erro ao realizar a vinculação da lista de materiais e processos.', 'danger')
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
    return redirect(url_for('engenharia'))

@app.route('/deletar_item_estrutura/<int:id>', methods=['POST'])
def deletar_item_estrutura(id):
    """Remove um componente ou máquina vinculada à engenharia"""
    if not session.get('logado'):
        return redirect(url_for('index'))
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM estrutura_produto WHERE id = %s', (id,))
        conn.commit()
        flash('Item da estrutura removido com sucesso!', 'success')
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao deletar item da estrutura no Neon: {e}")
        flash('Erro ao deletar o componente selecionado da engenharia.', 'danger')
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
    return redirect(url_for('engenharia'))
# ==============================================================================
# PARTE 21 DE 23: MÓDULO DE PRECIFICAÇÃO, CARTEIRA DE VENDAS E CONTROLE DE ESTOQUE
# ==============================================================================

@app.route('/precificacao')
def precificacao():
    """Gera a consolidação de custos industriais de fabricação (Custo Técnico Primário)"""
    if not session.get('logado'):
        return redirect(url_for('index'))
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
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
    except Exception as e:
        logger.error(f"Erro ao carregar módulo de precificação: {e}")
        prods, salvos = [], []
        caixa, total = 0.0, 0.0
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
    return render_template('precificacao.html', produtos=prods, precos_salvos=salvos, caixa_disponivel=caixa, capital_inicial=total)

@app.route('/salvar_preco', methods=['POST'])
def salvar_preco():
    """Salva ou substitui de forma dinâmica o preço de venda estratégico no Neon (UPSERT)"""
    if not session.get('logado'):
        return redirect(url_for('index'))
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO formacao_precos (produto_id, imposto_municipal, imposto_estadual, imposto_federal, margem_lucro, preco_venda_final) 
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (produto_id) 
            DO UPDATE SET imposto_municipal = EXCLUDED.imposto_municipal, 
                          imposto_estadual = EXCLUDED.imposto_estadual, 
                          imposto_federal = EXCLUDED.imposto_federal, 
                          margem_lucro = EXCLUDED.margem_lucro, 
                          preco_venda_final = EXCLUDED.preco_venda_final;
        ''', (int(request.form.get('produto_id') or 0), float(request.form.get('imposto_municipal') or 0), float(request.form.get('imposto_estadual') or 0), float(request.form.get('imposto_federal') or 0), float(request.form.get('margem_lucro') or 0), float(request.form.get('preco_venda_final') or 0)))
        conn.commit()
        flash('Preço de venda final definido e salvo estrategicamente!', 'success')
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao salvar preço no Neon: {e}")
        flash('Erro ao salvar formação de preços no banco de dados.', 'danger')
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
    return redirect(url_for('precificacao'))

@app.route('/vendas')
def vendas():
    """Gera a carteira consolidada de pedidos comerciais e faturamentos"""
    if not session.get('logado'):
        return redirect(url_for('index'))
    conn = conexao_pool.getconn()
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
    except Exception as e:
        logger.error(f"Erro ao carregar carteira de vendas: {e}")
        prods, peds = [], []
        caixa, total = 0.0, 0.0
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
    return render_template('vendas.html', produtos=prods, pedidos=peds, caixa_disponivel=caixa, capital_inicial=total)

@app.route('/estoque')
def estoque():
    """Visão de controle do Almoxarifado central de produtos acabados"""
    if not session.get('logado'):
        return redirect(url_for('index'))
    conn = conexao_pool.getconn()
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
    except Exception as e:
        logger.error(f"Erro ao processar visão de estoque: {e}")
        itens, peds = [], []
        caixa, total = 0.0, 0.0
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
    return render_template('estoque.html', estoque_itens=itens, pedidos=peds, caixa_disponivel=caixa, capital_inicial=total)

@app.route('/lancar_venda', methods=['POST'])
def lancar_venda():
    """Lança uma nova transação comercial deduzindo ou encomendando via PCP"""
    if not session.get('logado'):
        return redirect(url_for('index'))
    prod_id = int(request.form.get('produto_id') or 0)
    qtd = int(request.form.get('quantidade') or 1)
    conn = conexao_pool.getconn()
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
        flash('Movimentação comercial lançada com sucesso!', 'success')
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao lançar transação comercial: {e}")
        flash('Erro ao processar o lançamento da venda.', 'danger')
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
    return redirect(url_for('vendas'))

@app.route('/deletar_venda/<int:id>', methods=['POST'])
def deletar_venda(id):
    """Estorna e remove um pedido da carteira de vendas"""
    if not session.get('logado'):
        return redirect(url_for('index'))
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM pedidos_vendas WHERE id = %s', (id,))
        conn.commit()
        flash('Pedido de venda cancelado com sucesso.', 'success')
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao deletar venda no Neon: {e}")
        flash('Erro ao tentar excluir o registro de venda.', 'danger')
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
    return redirect(url_for('vendas'))
# ==============================================================================
# PARTE 22 DE 23: CENTRAL DE PCP, GERENCIAMENTO DE OPERAÇÕES E NOTA FISCAL
# ==============================================================================

@app.route('/pcp')
def pcp():
    """Módulo de Planejamento e Controle da Produção (Sequenciamento de OPs)"""
    if not session.get('logado'):
        return redirect(url_for('index'))
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id, pedido_id, numero_operacao, maquina_name, codigo_produto, nome_produto, data_entrada, tempo_estimado_min, data_saida, operador_nome, status, custo_operacao FROM ordens_processo ORDER BY pedido_id ASC, id ASC')
        ords = cursor.fetchall()
        caixa, total = calcular_caixa_disponivel(conn)
    except Exception as e:
        logger.error(f"Erro ao processar painel de PCP: {e}")
        ords = []
        caixa, total = 0.0, 0.0
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
    return render_template('pcp.html', ordens=ords, caixa_disponivel=caixa, capital_inicial=total)

@app.route('/solicitar_producao_pcp/<int:pedido_id>', methods=['POST'])
def solicitar_producao_pcp(pedido_id):
    """Explode a árvore de engenharia em Ordens de Processo cronológicas na fila do PCP"""
    if not session.get('logado'):
        return redirect(url_for('index'))
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id FROM ordens_processo WHERE pedido_id = %s', (pedido_id,))
        if not cursor.fetchone():
            cursor.execute('SELECT pv.id, pv.produto_id, pv.quantidade, p.codigo_produto, p.nome_produto FROM pedidos_vendas pv JOIN produtos p ON pv.produto_id = p.id WHERE pv.id = %s', (pedido_id,))
            ped = cursor.fetchone()
            if ped:
                prod_id_ped, qtd_ped, cod_prod_ped, nome_prod_ped = ped[1], int(ped[2]), ped[3], ped[4]
                cursor.execute('SELECT ep.id, ep.produto_id, ep.maquina_id, ep.material_id, ep.tempo_processo_min, ep.quantidade_material, m.nome_equipamento, m.custo_minuto_maquina, m.operador_nome FROM estrutura_produto ep LEFT JOIN maquinas m ON ep.maquina_id = m.id WHERE ep.produto_id = %s ORDER BY ep.id ASC', (prod_id_ped,))
                rots = cursor.fetchall()
                ponteiro_tempo = datetime.datetime.now()
                tempo_setup_fixo = 15
                for idx, r in enumerate(rots):
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
        logger.error(f"Erro no agendamento do PCP no Neon: {e}")
        flash('Erro operacional ao processar ordens.', 'danger')
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
    return redirect(url_for('estoque'))

@app.route('/abastecer_estoque_pcp', methods=['POST'])
def abastecer_estoque_pcp():
    """Libera o lote finalizado do PCP e realiza a entrada física de acabados no estoque"""
    if not session.get('logado'):
        return redirect(url_for('index'))
    prod_id = int(request.form.get('produto_id') or 0)
    pedido_id = int(request.form.get('pedido_id') or 0)
    qtd = float(request.form.get('quantidade_abastecer') or 0)
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
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
        logger.error(f"Erro no almoxarifado do Neon: {e}")
        flash('Erro operacional ao processar abastecimento de estoque.', 'danger')
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
    return redirect(url_for('estoque'))

@app.route('/dar_baixa_op/<int:id>', methods=['POST'])
def dar_baixa_op(id):
    """Baixa operacional e encerramento de estágio de uma Ordem de Processo no chão de fábrica"""
    if not session.get('logado'):
        return redirect(url_for('index'))
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE ordens_processo SET operador_nome = %s, status = \'Finalizado\' WHERE id = %s', (request.form.get('operador_nome', 'Operador'), id))
        conn.commit()
        flash('Ordem de Processo finalizada com sucesso!', 'success')
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao baixar OP no Neon: {e}")
        flash('Erro ao tentar dar baixa na Ordem de Processo.', 'danger')
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
    return redirect(url_for('pcp'))

@app.route('/imprimir_nf/<int:pedido_id>')
def imprimir_nf(pedido_id):
    """Gera e renderiza a Nota Fiscal Eletrônica e alíquotas tributárias integradas (DRE)"""
    if not session.get('logado'):
        return redirect(url_for('index'))
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT pv.id, pv.produto_id, pv.quantidade, pv.desconto_percentual, pv.observacoes, pv.data_pedido,
                   p.codigo_produto, p.nome_produto, fp.preco_venda_final, fp.imposto_municipal, fp.imposto_estadual, fp.imposto_federal 
            FROM pedidos_vendas pv 
            JOIN produtos p ON pv.produto_id = p.id 
            JOIN formacao_precos fp ON p.id = fp.produto_id 
            WHERE pv.id = %s
        ''', (pedido_id,))
        row = cursor.fetchone()
    except Exception as e:
        logger.error(f"Erro ao buscar nota fiscal no Neon: {e}")
        row = None
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
    if not row: 
        return "Nota Fiscal não encontrada."
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
    return render_template('nota_fiscal.html', p=ped, subtotal=sub, v_desconto=v_desc, total_liquido=liq, v_municipal=v_mun, v_estadual=v_est, v_federal=v_fed, total_impostos=v_mun+v_est+v_fed)
# ==============================================================================
# PARTE 23 DE 23: BALANCETE CONTÁBIL, INDICADORES DE ROI E INICIALIZAÇÃO DO APP
# ==============================================================================

@app.route('/financeiro')
def financeiro():
    """Gera o Balancete Contábil e o demonstrativo DRE estruturado da empresa"""
    if not session.get('logado'):
        return redirect(url_for('index'))
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT COALESCE(SUM(fp.preco_venda_final * pv.quantidade), 0) FROM pedidos_vendas pv JOIN formacao_precos fp ON pv.produto_id = fp.produto_id')
        faturamento_bruto = float(cursor.fetchone() or 0.0)
        cursor.execute("SELECT COALESCE(SUM(salario_base + valor_adicionais), 0) FROM maquinas WHERE operador_nome != 'Posto Vago - Aguardando MOD' AND operador_nome != ''")
        despesa_pessoal_bruta = float(cursor.fetchone() or 0.0)
        cursor.execute('SELECT COALESCE(SUM((fp.preco_venda_final * pv.quantidade) * ((fp.imposto_municipal + fp.imposto_estadual + fp.imposto_federal) / 100.0)), 0) FROM pedidos_vendas pv JOIN formacao_precos fp ON pv.produto_id = fp.produto_id')
        impostos_vendas = float(cursor.fetchone() or 0.0)
        caixa, total = calcular_caixa_disponivel(conn)
    except Exception as e:
        logger.error(f"Erro ao carregar módulo financeiro: {e}")
        faturamento_bruto, despesa_pessoal_bruta, impostos_vendas, caixa, total = 0.0, 0.0, 0.0, 0.0, 0.0
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
    total_encargos = impostos_vendas + (despesa_pessoal_bruta * 0.20)
    return render_template('financeiro.html', faturamento=faturamento_bruto, custo_pessoal=despesa_pessoal_bruta, impostos=total_encargos, saldo_liquido=caixa, caixa_disponivel=caixa, capital_inicial=total)

@app.route('/pagar_dividendos', methods=['POST'])
def pagar_dividendos():
    """Simula a distribuição de dividendos e participação dos acionistas"""
    if not session.get('logado'):
        return redirect(url_for('index'))
    percentual = float(request.form.get('percentual_lucro') or 25)
    flash(f'Distribuição de {percentual}% dos dividendos processada com sucesso!', 'success')
    return redirect(url_for('financeiro'))

@app.route('/roi')
def roi():
    """Central de Indicadores de Desempenho Econômico (Retorno sobre Investimento e Payback)"""
    if not session.get('logado'):
        return redirect(url_for('index'))
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT COALESCE(SUM(fp.preco_venda_final * pv.quantidade), 0), COALESCE(SUM(pv.quantidade), 0) FROM pedidos_vendas pv JOIN formacao_precos fp ON pv.produto_id = fp.produto_id')
        v_dados = cursor.fetchone()
        cursor.execute('SELECT COALESCE(SUM(valor_imovel_estimado + capital_inicial_negocio), 0), COALESCE(SUM(aluguel_regional), 0) FROM investimentos_imobiliarios')
        invs = cursor.fetchone()
        cursor.execute("SELECT COALESCE(SUM(salario_base + valor_adicionais), 0) FROM maquinas WHERE operador_nome != 'Posto Vago - Aguardando MOD' AND operador_nome != ''")
        despesa_pessoal = float(cursor.fetchone() or 0.0)
        caixa, total = calcular_caixa_disponivel(conn)
    except Exception as e:
        logger.error(f"Erro ao calcular métricas de ROI: {e}")
        v_dados, invs, despesa_pessoal, caixa, total = [0.0, 0.0], [0.0, 0.0], 0.0, 0.0, 0.0
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
    rec, pecas = float(v_dados or 0.0), float(v_dados or 0.0)
    cap, aluguel = float(invs or 0.0), float(invs or 0.0)
    sobra = rec - despesa_pessoal - aluguel
    payback_meses = (cap / sobra) if sobra > 0 else 0.0
    return render_template('roi.html', receita=rec, total_pecas=pecas, capital=cap, payback_real=payback_meses, lucro_acionistas=rec * 0.25, caixa_disponivel=caixa, capital_inicial=total)

# Instanciação estrutural obrigatória sob escopo ativo do Flask para evitar concorrência em produção
with app.app_context():
    inicializar_banco()
    complementar_tabelas()
    popular_dados_iniciais()

if __name__ == '__main__':
    app.run(debug=True)
