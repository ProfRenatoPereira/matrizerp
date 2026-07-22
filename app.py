import os
import math
import logging
import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from whitenoise import WhiteNoise
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from psycopg2 import pool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "teradmas_secret_key_2026")
app.wsgi_app = WhiteNoise(app.wsgi_app, root="static/")

CATALOGO_MAQUINAS = {
    "001 - Torno CNC Industrial": {
        "nome": "Torno CNC Industrial", "custo_minuto": 0.4500, "pot": 15.0, "cons": 11.2,
        "vel": "3000 RPM", "avan": "15000 mm/min", "comp": 1000, "diam": 500, "mnt": 500,
        "preco": 250000.00, "dep": 2083.33, "venda": 50000.00,
        "operador": "Operador Especializado de Torno CNC", "custo_op": 0.3500, "salario": 3500.00,
        "adic": 700.00, "vida": 120
    },
    "002 - Fresadora Universal": {
        "nome": "Fresadora Universal", "custo_minuto": 0.3800, "pot": 7.5, "cons": 5.6,
        "vel": "1800 RPM", "avan": "800 mm/min", "comp": 800, "diam": 400, "mnt": 350,
        "preco": 120000.00, "dep": 1000.00, "venda": 24000.00,
        "operador": "Fresador Universal", "custo_op": 0.2800, "salario": 2800.00,
        "adic": 560.00, "vida": 120
    },
    "003 - Furadeira de Bancada": {
        "nome": "Furadeira de Bancada", "custo_minuto": 0.1500, "pot": 1.5, "cons": 1.1,
        "vel": "2500 RPM", "avan": "Manual", "comp": 300, "diam": 150, "mnt": 80,
        "preco": 8000.00, "dep": 66.67, "venda": 1600.00,
        "operador": "Auxiliar de Produção", "custo_op": 0.1600, "salario": 1600.00,
        "adic": 0.00, "vida": 120
    },
    "004 - Retífica Cilíndrica": {
        "nome": "Retífica Cilíndrica", "custo_minuto": 0.5200, "pot": 11.0, "cons": 8.2,
        "vel": "4500 RPM", "avan": "2000 mm/min", "comp": 600, "diam": 300, "mnt": 600,
        "preco": 180000.00, "dep": 1500.00, "venda": 36000.00,
        "operador": "Retificador Especializado", "custo_op": 0.3800, "salario": 3800.00,
        "adic": 760.00, "vida": 120
    },
    "005 - Centro de Usinagem": {
        "nome": "Centro de Usinagem", "custo_minuto": 0.8500, "pot": 22.0, "cons": 16.5,
        "vel": "12000 RPM", "avan": "30000 mm/min", "comp": 1200, "diam": 600, "mnt": 1200,
        "preco": 550000.00, "dep": 4583.33, "venda": 110000.00,
        "operador": "Programador e Operador de Centro de Usinagem", "custo_op": 0.4800, "salario": 4800.00,
        "adic": 960.00, "vida": 120
    }
}

CATALOGO_MATERIAIS = {
    "Aço SAE 1020": {"cod": "MAT-ACO-1020", "nome": "Barra de Aço Carbono SAE 1020", "preco": 45.50, "dim": "Ø 3\" x 1000mm", "vol": 100.0},
    "Aço SAE 4140": {"cod": "MAT-ACO-4140", "nome": "Barra de Aço Aliado SAE 4140", "preco": 125.00, "dim": "Ø 2\" x 1000mm", "vol": 50.0},
    "Alumínio 6061": {"cod": "MAT-ALU-6061", "nome": "Tarugo de Alumínio Naval 6061-T6", "preco": 85.00, "dim": "Ø 4\" x 500mm", "vol": 80.0},
    "Polímero Nylon 6.6": {"cod": "MAT-NYLON-66", "nome": "Tarugo de Nylon 6.6 Técnico", "preco": 35.00, "dim": "Ø 50mm x 1000mm", "vol": 120.0}
}

DATABASE_URL = os.environ.get("DATABASE_URL")
try:
    if DATABASE_URL:
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        conexao_pool = pool.ThreadedConnectionPool(minconn=1, maxconn=10, dsn=DATABASE_URL, sslmode='require')
    else:
        conexao_pool = pool.ThreadedConnectionPool(minconn=1, maxconn=5, dsn="dbname=matrizerp user=postgres password=postgres host=localhost")
except Exception as e:
    logger.critical(f"Erro no Pool: {e}")
    raise e

def inicializar_banco():
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        # --- TABELAS ORIGINAIS DO SEU SISTEMA ---
        cursor.execute('CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, usuario VARCHAR(150) UNIQUE NOT NULL, senha VARCHAR(255) NOT NULL);')
        cursor.execute('CREATE TABLE IF NOT EXISTS investimentos_imobiliarios (id SERIAL PRIMARY KEY, turma_nome VARCHAR(255), cidade_regiao VARCHAR(255), bairro_imovel VARCHAR(255), area_imovel NUMERIC(10,2), taxa_selic NUMERIC(5,2), valor_imovel_estimado NUMERIC(12,2), aluguel_regional NUMERIC(12,2), perc_acionistas NUMERIC(5,2), capital_inicial_negocio NUMERIC(15,2));')
        cursor.execute('CREATE TABLE IF NOT EXISTS maquinas (id SERIAL PRIMARY KEY, nome_equipamento VARCHAR(255) NOT NULL, potencia NUMERIC(10,2), consumo_eletrico NUMERIC(10,2), velocidade VARCHAR(100), avanco VARCHAR(100), comprimento_max INTEGER, diametro_max INTEGER, frequencia_manutencao INTEGER, horas_trabalhadas INTEGER DEFAULT 0, preco_compra NUMERIC(12,2), depreciacao_mensal NUMERIC(10,2), valor_venda_final NUMERIC(12,2), custo_minuto_maquina NUMERIC(10,4), operador_nome VARCHAR(255), custo_minuto_operador NUMERIC(10,4), salario_base NUMERIC(10,2), valor_adicionais NUMERIC(10,2), turno_trabalho VARCHAR(100) DEFAULT \'Diurno\', dia_semana VARCHAR(100) DEFAULT \'Regular\', vida_util_meses INTEGER);')
        cursor.execute('CREATE TABLE IF NOT EXISTS materiais (id SERIAL PRIMARY KEY, codigo_material VARCHAR(100) UNIQUE NOT NULL, nome_material VARCHAR(255) NOT NULL, preco_unidade NUMERIC(10,2), dimensoes VARCHAR(100), volume_disponivel NUMERIC(10,2));')
        cursor.execute('CREATE TABLE IF NOT EXISTS produtos (id SERIAL PRIMARY KEY, codigo_produto VARCHAR(100) UNIQUE NOT NULL, nome_produto VARCHAR(255) NOT NULL, custo_total_fabricacao NUMERIC(10,2) DEFAULT 0.0);')
        cursor.execute('CREATE TABLE IF NOT EXISTS estrutura_produto (id SERIAL PRIMARY KEY, produto_id INTEGER REFERENCES produtos(id) ON DELETE CASCADE, material_id INTEGER REFERENCES materiais(id) ON DELETE CASCADE, quantidade_necessaria NUMERIC(10,2) NOT NULL);')
        cursor.execute('CREATE TABLE IF NOT EXISTS formacao_precos (id SERIAL PRIMARY KEY, produto_id INTEGER REFERENCES produtos(id) ON DELETE CASCADE, custo_material NUMERIC(10,2), custo_maquina NUMERIC(10,2), custo_trabalho NUMERIC(10,2), despesas_fixas NUMERIC(5,2), lucro_desejado NUMERIC(5,2), impuestos NUMERIC(5,2), preco_venda_sugerido NUMERIC(10,2));')
        cursor.execute('CREATE TABLE IF NOT EXISTS pedidos_vendas (id SERIAL PRIMARY KEY, cliente_nome VARCHAR(255), produto_id INTEGER REFERENCES produtos(id) ON DELETE CASCADE, quantidade INTEGER NOT NULL, preco_unitario_pactuado NUMERIC(10,2), faturamento_total NUMERIC(12,2), status_pedido VARCHAR(50) DEFAULT \'Pendente\');')
        cursor.execute('CREATE TABLE IF NOT EXISTS ordens_processo (id SERIAL PRIMARY KEY, pedido_id INTEGER REFERENCES pedidos_vendas(id) ON DELETE CASCADE, maquina_id INTEGER REFERENCES maquinas(id) ON DELETE CASCADE, tempo_estimado_minutos INTEGER, custo_total_estimado NUMERIC(10,2), status_ordem VARCHAR(50) DEFAULT \'Agendado\');')
        cursor.execute('CREATE TABLE IF NOT EXISTS estoque_produtos (id SERIAL PRIMARY KEY, produto_id INTEGER REFERENCES produtos(id) ON DELETE CASCADE, quantidade_disponivel INTEGER DEFAULT 0);')
        
        # --- NOVAS TABELAS DO MÓDULO ERP PEDAGÓGICO ---
        cursor.execute('CREATE TABLE IF NOT EXISTS alunos (id SERIAL PRIMARY KEY, nome VARCHAR(255) NOT NULL, cpf VARCHAR(14) UNIQUE, data_matricula TIMESTAMP DEFAULT CURRENT_TIMESTAMP);')
        cursor.execute('CREATE TABLE IF NOT EXISTS turmas (id SERIAL PRIMARY KEY, nome_turma VARCHAR(50) NOT NULL, ano_letivo INTEGER NOT NULL);')
        cursor.execute('CREATE TABLE IF NOT EXISTS disciplinas (id SERIAL PRIMARY KEY, nome_disciplina VARCHAR(100) NOT NULL);')
        cursor.execute('CREATE TABLE IF NOT EXISTS boletim (id SERIAL PRIMARY KEY, aluno_id INTEGER REFERENCES alunos(id) ON DELETE CASCADE, turma_id INTEGER REFERENCES turmas(id) ON DELETE CASCADE, disciplina_id INTEGER REFERENCES disciplinas(id) ON DELETE CASCADE, nota_b1 NUMERIC(4,2), nota_b2 NUMERIC(4,2), total_faltas INTEGER DEFAULT 0);')

        # Criação automática de um usuário Administrador padrão (Senha: admin123) se a tabela estiver vazia
        cursor.execute("SELECT COUNT(*) FROM usuarios;")
        if cursor.fetchone()[0] == 0:
            from werkzeug.security import generate_password_hash
            senha_criptografada = generate_password_hash("admin123")
            cursor.execute("INSERT INTO usuarios (usuario, senha) VALUES (%s, %s);", ("admin", senha_criptografada))

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conexao_pool.putconn(conn)

inicializar_banco()
def calcular_caixa_disponivel(conn):
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COALESCE(SUM(capital_inicial_negocio), 0) FROM investimentos_imobiliarios;")
        total_investido = float(cursor.fetchone()[0])
        cursor.execute("SELECT COALESCE(SUM(preco_compra), 0) FROM maquinas;")
        gasto_maquinas = float(cursor.fetchone()[0])
        cursor.execute("SELECT COALESCE(SUM(preco_unidade * volume_disponivel), 0) FROM materiais;")
        gasto_materiais = float(cursor.fetchone()[0])
        cursor.execute("SELECT COALESCE(SUM(faturamento_total), 0) FROM pedidos_vendas WHERE status_pedido = 'Faturado';")
        faturamento = float(cursor.fetchone()[0])
        cursor.execute("SELECT COALESCE(SUM(salario_base + valor_adicionais), 0) FROM maquinas;")
        folha_rh = float(cursor.fetchone()[0])
        cursor.execute("SELECT COALESCE(SUM(aluguel_regional), 0) FROM investimentos_imobiliarios;")
        custo_aluguel = float(cursor.fetchone()[0])
        caixa_calculado = total_investido - gasto_maquinas - gasto_materiais + faturamento - folha_rh - custo_aluguel
        return caixa_calculado, total_investido
    except Exception as e:
        if 'logger' in globals():
            logger.error(f"Erro caixa: {e}")
        else:
            print(f"Erro caixa: {e}")
        return 0.0, 0.0
    finally:
        cursor.close()  # Correção aplicada: Removido o erro de sintaxe do cursor solto

@app.route('/')
def index():
    if session.get('logado'):
        return redirect(url_for('estrutura'))
    return render_template('login.html')

# Ajustado para receber a ação '/login_validar' do seu HTML e evitar o Erro 404
@app.route('/login_validar', methods=['POST'])
@app.route('/login', methods=['POST'])
def login():
    usuario = request.form.get('usuario')
    senha = request.form.get('senha')
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT senha FROM usuarios WHERE usuario = %s", (usuario,))
        resultado = cursor.fetchone()
        if resultado and check_password_hash(resultado[0], senha):
            session['logado'] = True
            session['usuario'] = usuario
            flash('Autenticação realizada com sucesso!', 'success')
            return redirect(url_for('estrutura'))
        else:
            flash('Credenciais de acesso incorretas.', 'danger')
            return redirect(url_for('index'))
    except Exception as e:
        flash('Erro interno ao processar a autenticação.', 'danger')
        return redirect(url_for('index'))
    finally:
        cursor.close()
        conexao_pool.putconn(conn)

@app.route('/logout')
def logout():
    session.clear()
    flash('Sessão encerrada.', 'info')
    return redirect(url_for('index'))
@app.route('/salvar_estrutura', methods=['POST'])
def salvar_estrutura():
    if not session.get('logado'):
        return redirect(url_for('index'))
    return estrutura()

@app.route('/estrutura', methods=['GET', 'POST'])
def estrutura():
    if not session.get('logado'):
        return redirect(url_for('index'))
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        if request.method == 'POST':
            turma = request.form.get('turma_nome')
            regiao = request.form.get('cidade_regiao')
            bairro = request.form.get('bairro_imovel')
            area = float(request.form.get('area_imovel', 0) or 0)
            taxa_selic = 11.25
            valor_imovel = area * 2800.00
            aluguel = valor_imovel * 0.005
            perc_acionistas = 50.00
            capital_inicial = valor_imovel * 1.5
            cursor.execute('INSERT INTO investimentos_imobiliarios (turma_nome, city_regiao, bairro_imovel, area_imovel, taxa_selic, valor_imovel_estimado, aluguel_regional, perc_acionistas, capital_inicial_negocio) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);', (turma, regiao, bairro, area, taxa_selic, valor_imovel, aluguel, perc_acionistas, capital_inicial))
            conn.commit()
            flash('Simulação imobiliária salva!', 'success')
            
        cursor.execute("SELECT id, turma_nome, cidade_regiao, bairro_imovel, area_imovel, taxa_selic, valor_imovel_estimado, aluguel_regional, perc_acionistas, capital_inicial_negocio FROM investimentos_imobiliarios ORDER BY id DESC;")
        simulacoes = cursor.fetchall()
        
        # Chama a função passando a conexão ativa de forma segura
        caixa, total = calcular_caixa_disponivel(conn)
    except Exception as e:
        if conn:
            conn.rollback()
        simulacoes = []
        caixa, total = 0.0, 0.0
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
    return render_template('estrutura.html', simulacoes=simulacoes, caixa_disponivel=caixa, capital_inicial=total)

@app.route('/rh')
def rh():
    if not session.get('logado'):
        return redirect(url_for('index'))
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, nome_equipamento, operador_nome, salario_base, valor_adicionais, turno_trabalho, dia_semana FROM maquinas ORDER BY id ASC;")
        funcionarios = cursor.fetchall()
        caixa, total = calcular_caixa_disponivel(conn)
    except Exception as e:
        funcionarios = []
        caixa, total = 0.0, 0.0
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
    return render_template('rh.html', funcionarios=funcionarios, caixa_disponivel=caixa, capital_inicial=total)

@app.route('/maquinas', methods=['GET', 'POST'])
def maquinas():
    if not session.get('logado'):
        return redirect(url_for('index'))
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        if request.method == 'POST':
            equip_sel = request.form.get('equipamento_catalogo')
            turno = request.form.get('turno_trabalho', 'Diurno')
            dia = request.form.get('dia_semana', 'Regular')
            if equip_sel in CATALOGO_MAQUINAS:
                d = CATALOGO_MAQUINAS[equip_sel]
                cursor.execute('INSERT INTO maquinas (nome_equipamento, potencia, consumo_eletrico, velocidade, avanco, comprimento_max, diametro_max, frequencia_manutencao, preco_compra, depreciacao_mensal, valor_venda_final, custo_minuto_maquina, operador_nome, custo_minuto_operador, salario_base, valor_adicionais, turno_trabalho, dia_semana, vida_util_meses) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);', (d['nome'], d['pot'], d['cons'], d['vel'], d['avan'], d['comp'], d['diam'], d['mnt'], d['preco'], d['dep'], d['venda'], d['custo_minuto'], d['operador'], d['custo_op'], d['salario'], d['adic'], turno, dia, d['vida']))
                conn.commit()
                flash(f"Equipamento {d['nome']} adquirido!", "success")
        cursor.execute('SELECT id, nome_equipamento, potencia, consumo_eletrico, velocidade, avanco, preco_compra, depreciacao_mensal, custo_minuto_maquina, operador_nome FROM maquinas ORDER BY id ASC;')
        lista_maquinas = cursor.fetchall()
        caixa, total = calcular_caixa_disponivel(conn)
    except Exception as e:
        if conn:
            conn.rollback()
        lista_maquinas = []
        caixa, total = 0.0, 0.0
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
    return render_template('maquinas.html', maquinas=lista_maquinas, catalogo=CATALOGO_MAQUINAS, caixa_disponivel=caixa, capital_inicial=total)
@app.route('/imprimir_holerite/<int:id>')
def imprimir_holerite(id):
    if not session.get('logado'):
        return redirect(url_for('index'))
    tipo = request.args.get('tipo', 'mensal')
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT nome_equipamento, operador_nome, salario_base, valor_adicionais, turno_trabalho FROM maquinas WHERE id = %s;", (id,))
        func = cursor.fetchone()
        if not func:
            return redirect(url_for('rh'))
        
        sb = float(func[2])
        va = float(func[3])
        salario_bruto = sb + va
        
        # Tabelas de cálculo do INSS
        if salario_bruto <= 1412.00: inss = salario_bruto * 0.075
        elif salario_bruto <= 2666.68: inss = (salario_bruto * 0.09) - 21.18
        elif salario_bruto <= 4000.03: inss = (salario_bruto * 0.12) - 101.18
        elif salario_bruto <= 7786.02: inss = (salario_bruto * 0.14) - 181.18
        else: inss = 908.85
        
        # Tabelas de cálculo do IRRF
        base_irrf = salario_bruto - inss
        if base_irrf <= 2112.00: irrf = 0.0
        elif base_irrf <= 2826.65: irrf = (base_irrf * 0.075) - 158.40
        elif base_irrf <= 3751.05: irrf = (base_irrf * 0.15) - 370.40
        elif base_irrf <= 4664.68: irrf = (base_irrf * 0.225) - 651.73
        else: irrf = (base_irrf * 0.275) - 884.96
        
        vt = salario_bruto * 0.06 if func[4] == 'Diurno' else 0.0
        
        # Objeto holerite estruturado para injeção no template holerite.html
        holerite = {
            "operador": func[1], 
            "cargo": "Operador Industrial / Instrutor", 
            "maquina": func[0], 
            "bruto": round(salario_bruto, 2), 
            "inss": round(inss, 2), 
            "irrf": round(irrf, 2), 
            "vt": round(vt, 2), 
            "liquido": round(salario_bruto - inss - irrf - vt, 2), 
            "data": datetime.datetime.now().strftime("%d/%m/%Y"), 
            "tipo": tipo.upper()
        }
    except Exception as e:
        if conn:
            conn.rollback()
        holerite = None
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
    return render_template('holerite.html', holerite=holerite)

@app.route('/almoxarifado', methods=['GET', 'POST'])
def almoxarifado():
    if not session.get('logado'):
        return redirect(url_for('index'))
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        if request.method == 'POST':
            mat_sel = request.form.get('material_catalogo')
            qtd_input = request.form.get('quantidade_compra', 0)
            qtd = float(qtd_input) if qtd_input else 0.0
            
            if mat_sel in CATALOGO_MATERIAIS and qtd > 0:
                mat = CATALOGO_MATERIAIS[mat_sel]
                cursor.execute("SELECT id, volume_disponivel FROM materiais WHERE codigo_material = %s;", (mat['cod'],))
                existe = cursor.fetchone()
                if existe:
                    # Garante conversão segura mesmo se o retorno do banco for None ou Decimal
                    vol_atual = float(existe[1]) if existe[1] is not None else 0.0
                    cursor.execute("UPDATE materiais SET volume_disponivel = %s WHERE id = %s;", (vol_atual + qtd, existe[0]))
                else:
                    cursor.execute('INSERT INTO materiais (codigo_material, nome_material, preco_unidade, dimensoes, volume_disponivel) VALUES (%s, %s, %s, %s, %s);', (mat['cod'], mat['nome'], mat['preco'], mat['dim'], qtd))
                conn.commit()
                flash('Almoxarifado atualizado com sucesso!', 'success')
                
        cursor.execute("SELECT id, codigo_material, nome_material, preco_unidade, dimensoes, volume_disponivel FROM materiais ORDER BY id ASC;")
        estoque = cursor.fetchall()
        caixa, total = calcular_caixa_disponivel(conn)
    except Exception as e:
        if conn:
            conn.rollback()
        estoque = []
        caixa, total = 0.0, 0.0
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
    return render_template('almoxarifado.html', estoque=estoque, catalogo=CATALOGO_MATERIAIS, caixa_disponivel=caixa, capital_inicial=total)
@app.route('/produtos', methods=['GET', 'POST'])
def produtos():
    if not session.get('logado'): 
        return redirect(url_for('index'))
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        if request.method == 'POST':
            cod = request.form.get('codigo_produto')
            nome = request.form.get('nome_produto')
            if cod and nome:
                cursor.execute('INSERT INTO produtos (codigo_produto, nome_produto) VALUES (%s, %s) ON CONFLICT DO NOTHING;', (cod, nome))
                conn.commit()
                flash('Item de Engenharia/Matriz Cadastrado!', 'success')
        cursor.execute("SELECT id, codigo_produto, nome_produto, custo_total_fabricacao FROM produtos ORDER BY id ASC;")
        lista_prod = cursor.fetchall()
        caixa, total = calcular_caixa_disponivel(conn)
    except Exception as e:
        if conn:
            conn.rollback()
        lista_prod = []
        caixa, total = 0.0, 0.0
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
    return render_template('produtos.html', produtos=lista_prod, caixa_disponivel=caixa, capital_inicial=total)

@app.route('/vendas', methods=['GET', 'POST'])
def vendas():
    if not session.get('logado'): 
        return redirect(url_for('index'))
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        if request.method == 'POST':
            cliente = request.form.get('cliente_nome')
            p_id_raw = request.form.get('produto_id')
            qtd_raw = request.form.get('quantidade')
            preco_raw = request.form.get('preco_unitario')
            
            # Validação defensiva para impedir quebra do servidor por campos em branco
            if cliente and p_id_raw and qtd_raw and preco_raw:
                p_id = int(p_id_raw)
                qtd = int(qtd_raw)
                preco = float(preco_raw)
                faturamento_calculado = qtd * preco
                
                cursor.execute(
                    'INSERT INTO pedidos_vendas (cliente_nome, produto_id, quantidade, preco_unitario_pactuado, faturamento_total) VALUES (%s, %s, %s, %s, %s);', 
                    (cliente, p_id, qtd, preco, faturamento_calculado)
                )
                conn.commit()
                flash('Pedido comercial firmado e registrado!', 'success')
            else:
                flash('Falha ao registrar: Todos os campos do formulário devem ser preenchidos.', 'danger')
                
        cursor.execute("SELECT id, cliente_nome, produto_id, quantidade, preco_unitario_pactuado, faturamento_total, status_pedido FROM pedidos_vendas ORDER BY id DESC;")
        pedidos = cursor.fetchall()
        cursor.execute("SELECT id, nome_produto FROM produtos;")
        prods = cursor.fetchall()

        caixa, total = calcular_caixa_disponivel(conn)
    except Exception as e:
        if conn:
            conn.rollback()
        pedidos, prods = [], []
        caixa, total = 0.0, 0.0
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
    return render_template('vendas.html', pedidos=pedidos, produtos=prods, caixa_disponivel=caixa, capital_inicial=total)
@app.route('/faturar_pedido/<int:id>')
def faturar_pedido(id):
    if not session.get('logado'): 
        return redirect(url_for('index'))
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE pedidos_vendas SET status_pedido = 'Faturado' WHERE id = %s;", (id,))
        conn.commit()
        flash('Receita operacional faturada com sucesso no sistema!', 'success')
    except Exception as e:
        if conn:
            conn.rollback()
        flash('Ocorreu um erro operacional ao tentar faturar este registro.', 'danger')
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
    return redirect(url_for('vendas')

@app.route('/pcp', methods=['GET', 'POST'])
def pcp():
    if not session.get('logado'): 
        return redirect(url_for('index'))
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        if request.method == 'POST':
            ped_id_raw = request.form.get('pedido_id')
            maq_id_raw = request.form.get('maquina_id')
            tempo_raw = request.form.get('tempo_minutos')
            
            if ped_id_raw and maq_id_raw and tempo_raw:
                ped_id = int(ped_id_raw)
                maq_id = int(maq_id_raw)
                tempo = int(tempo_raw)
                
                cursor.execute('SELECT custo_minuto_maquina FROM maquinas WHERE id = %s;', (maq_id,))
                res_maquina = cursor.fetchone()
                
                if res_maquina:
                    c_min = float(res_maquina[0])
                    custo_total = tempo * c_min
                    
                    cursor.execute(
                        'INSERT INTO ordens_processo (pedido_id, maquina_id, tempo_estimado_minutos, custo_total_estimado) VALUES (%s, %s, %s, %s);', 
                        (ped_id, maq_id, tempo, custo_total)
                    )
                    conn.commit()
                    flash('Ordem de Produção roteirizada com sucesso no PCP!', 'success')
                else:
                    flash('Erro: Máquina selecionada não foi encontrada no banco.', 'danger')
            else:
                flash('Erro ao agendar: Todos os campos do formulário são obrigatórios.', 'danger')
                
        cursor.execute("SELECT id, pedido_id, maquina_id, tempo_estimado_minutos, custo_total_estimado, status_ordem FROM ordens_processo ORDER BY id DESC;")
        ordens = cursor.fetchall()
        
        cursor.execute("SELECT id, cliente_nome FROM pedidos_vendas WHERE status_pedido = 'Pendente';")
        p_pend = cursor.fetchall()
        
        cursor.execute("SELECT id, nome_equipamento FROM maquinas;")
        maqs = cursor.fetchall()
        
        caixa, total = calcular_caixa_disponivel(conn)
    except Exception as e:
        if conn:
            conn.rollback()
        ordens, p_pend, maqs = [], [], []
        caixa, total = 0.0, 0.0
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
    return render_template('pcp.html', ordens=ordens, pedidos=p_pend, maquinas=maqs, caixa_disponivel=caixa, capital_inicial=total)
@app.route('/professor_painel_secreto', methods=['GET', 'POST'])
def professor_painel_secreto():
    # Rota administrativa pública para controle de turmas em ambiente de laboratório
    conn = conexao_pool.getconn()
    cursor = conn.cursor()
    try:
        if request.method == 'POST':
            acao = request.form.get('acao_docente')
            if acao == 'RESET_COMPLETO':
                # Atualizado para incluir as tabelas acadêmicas no reset em cascata
                cursor.execute("""
                    TRUNCATE TABLE 
                        usuarios, investimentos_imobiliarios, maquinas, materiais, produtos, 
                        estrutura_produto, formacao_precos, pedidos_vendas, ordens_processo, 
                        estoque_produtos, alunos, turmas, disciplinas, boletim 
                    RESTART IDENTITY CASCADE;
                """)
                cursor.execute("INSERT INTO usuarios (usuario, senha) VALUES (%s, %s) ON CONFLICT DO NOTHING;", ("admin", generate_password_hash("admin123")))
                conn.commit()
                flash("Ambiente de Simulação e tabelas pedagógicas resetados com sucesso!", "danger")
            elif acao == 'CRIAR_EQUIPE':
                u = request.form.get('novo_usuario')
                s = request.form.get('nova_senha')
                if u and s:
                    cursor.execute("INSERT INTO usuarios (usuario, senha) VALUES (%s, %s) ON CONFLICT DO NOTHING;", (u, generate_password_hash(s)))
                    conn.commit()
                    flash(f"Equipe estudantil '{u}' registrada para a dinâmica!", "success")
        
        cursor.execute("SELECT id, usuario FROM usuarios ORDER BY id ASC;")
        usuarios = cursor.fetchall()
    except Exception as e:
        if conn:
            conn.rollback()
        usuarios = []
    finally:
        cursor.close()
        conexao_pool.putconn(conn)
    return render_template('professor.html', usuarios=usuarios)

if __name__ == '__main__':
    # Configuração de execução local dinâmica alinhada com as diretrizes do Render/Heroku
    porta_ambiente = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=porta_ambiente, debug=False)
