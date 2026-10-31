from fastapi import APIRouter, Request, Form, Depends, HTTPException, Cookie, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import json
import os
import shutil
import re
import calendar
from datetime import datetime, timedelta

from core.database import get_db
from core.modelos import Usuario, FolhaMensal, Notificacao
# Importamos as funções de segurança que vão ficar no main
from core.auth import decodificar_token, verificar_acesso
router = APIRouter()
templates = Jinja2Templates(directory="templates")

# =====================================================================
# MOTOR DE CÁLCULO E INTELIGÊNCIA DO PONTO
# =====================================================================
def calcular_relatorio_ponto(conteudo_txt: str, mes_referencia: str, config_calendario: dict, excecoes_individuais: dict = None, edicoes_manuais: dict = None, ferias_globais: dict = None):
    if excecoes_individuais is None: excecoes_individuais = {}
    if edicoes_manuais is None: edicoes_manuais = {}
    if ferias_globais is None: ferias_globais = {}
    
    linhas = conteudo_txt.strip().splitlines()
    registros = {}

    for linha in linhas:
        if "Tempo" in linha or not linha.strip(): continue
        partes = linha.split('\t')
        if len(partes) >= 4:
            nome = partes[1].strip().title()
            dh_parts = partes[3].strip().split()
            if len(dh_parts) == 2:
                data_txt, hora = dh_parts[0], dh_parts[1]
                if "/" in data_txt:
                    d, m, y = data_txt.split("/")
                    data = f"{y}-{m}-{d}"
                else: data = data_txt
                    
                if nome not in registros: registros[nome] = {}
                if data not in registros[nome]: registros[nome][data] = []
                registros[nome][data].append(hora)

    ano, mes = map(int, mes_referencia.split("-"))
    num_dias = calendar.monthrange(ano, mes)[1]
    JORNADA_DIARIA = 31680 # 8h48m
    
    dias_template = []
    for d in range(1, num_dias + 1):
        data_str = f"{ano}-{mes:02d}-{d:02d}"
        dt_obj = datetime(ano, mes, d)
        tipo = "Fim de Semana" if dt_obj.weekday() >= 5 else "Normal"
        if data_str in config_calendario: tipo = config_calendario[data_str]
        
        dias_template.append({
            "data_raw": data_str, "data_formatada": dt_obj.strftime("%d/%m/%Y"), "tipo_dia": tipo,
            "esperado": 0 if tipo in ["Feriado", "Fim de Semana"] else JORNADA_DIARIA
        })

    relatorio = []
    for nome, dias_batidos in registros.items():
        total_liquido_mes = 0; total_bruto_mes = 0; esperado_mes = 0
        err = 0; ok_d = 0; atr = 0; est = 0; faltas = 0
        detalhes_dias = []
        
        ferias_func = ferias_globais.get(nome)
        
        for dt in dias_template:
            data_str = dt["data_raw"]
            status_excecao = excecoes_individuais.get(nome, {}).get(data_str)
            is_folga_individual = (status_excecao == "Folga")
            is_aprovado = (status_excecao == "Aprovado")
            
            is_ferias = False
            if ferias_func and ferias_func["inicio"] and ferias_func["fim"]:
                if ferias_func["inicio"] <= data_str <= ferias_func["fim"]:
                    is_ferias = True
            
            if is_ferias:
                esperado_dia = 0
                tipo_dia_real = "Férias"
            elif is_folga_individual:
                esperado_dia = 31800 # 8h50m
                tipo_dia_real = "Folga Banco"
            else:
                esperado_dia = dt["esperado"]
                tipo_dia_real = dt["tipo_dia"]
            
            esperado_mes += esperado_dia
            
            if data_str in edicoes_manuais.get(nome, {}):
                batidas = edicoes_manuais[nome][data_str].copy()
                ajustado = True
            else:
                batidas = dias_batidos.get(data_str, []).copy()
                ajustado = False
            
            batidas.sort()
            auto_almoco = False
            bruto_dia_seg = 0
            liquido_dia_seg = 0
            
            if len(batidas) == 3:
                try:
                    b_str = [b if len(b) == 8 else f"{b}:00" for b in batidas]
                    t1, t2, t3 = datetime.strptime(b_str[0], "%H:%M:%S"), datetime.strptime(b_str[1], "%H:%M:%S"), datetime.strptime(b_str[2], "%H:%M:%S")
                    if t1.hour <= 11 and t3.hour >= 14:
                        novo_t = (t2 + timedelta(hours=1)) if t2.hour < 13 else (t2 - timedelta(hours=1))
                        batidas.append(novo_t.strftime("%H:%M:%S"))
                        batidas.sort()
                        auto_almoco = True
                except: pass

            if len(batidas) > 0:
                try:
                    h_in = batidas[0] if len(batidas[0])==8 else f"{batidas[0]}:00"
                    h_out = batidas[-1] if len(batidas[-1])==8 else f"{batidas[-1]}:00"
                    bruto_dia_seg = (datetime.strptime(h_out, "%H:%M:%S") - datetime.strptime(h_in, "%H:%M:%S")).total_seconds()
                except: pass
                
                for i in range(0, len(batidas)-1, 2):
                    try:
                        h1 = batidas[i] if len(batidas[i])==8 else f"{batidas[i]}:00"
                        h2 = batidas[i+1] if len(batidas[i+1])==8 else f"{batidas[i+1]}:00"
                        liquido_dia_seg += (datetime.strptime(h2, "%H:%M:%S") - datetime.strptime(h1, "%H:%M:%S")).total_seconds()
                    except: pass

            total_bruto_mes += bruto_dia_seg
            total_liquido_mes += liquido_dia_seg

            tem_erro_original = False
            if len(batidas) % 2 != 0: tem_erro_original = True
            elif len(batidas) > 0 and liquido_dia_seg < 7200: tem_erro_original = True
            
            inconsistente = tem_erro_original
            if is_aprovado: inconsistente = False
            
            bruto_str = f"{int(bruto_dia_seg//3600)}h {int((bruto_dia_seg%3600)//60):02d}m" if bruto_dia_seg > 0 else "--"
            liquido_str = f"{int(liquido_dia_seg//3600)}h {int((liquido_dia_seg%3600)//60):02d}m" if liquido_dia_seg > 0 else "--"

            if len(batidas) == 0:
                if esperado_dia > 0:
                    is_folga = (tipo_dia_real in ["Folga", "Folga Banco", "Férias"])
                    if not is_folga: faltas += 1
                    
                    detalhes_dias.append({
                        "data": dt["data_formatada"], "data_raw": data_str, "batidas": [], 
                        "inconsistente": False, "falta": not is_folga, "tipo_dia": tipo_dia_real, "esperado": esperado_dia,
                        "bruto_dia": "--", "total_dia": "--", 
                        "saldo_dia_str": f"-{int(esperado_dia//3600)}h {int((esperado_dia%3600)//60):02d}m",
                        "saldo_dia_positivo": False, "ajustado": ajustado, "auto_almoco": False, 
                        "atrasado": False, "almoco_longo": False, "aprovado": is_aprovado, "tem_erro_original": False
                    })
                else:
                    detalhes_dias.append({
                        "data": dt["data_formatada"], "data_raw": data_str, "batidas": [], 
                        "inconsistente": False, "falta": False, "tipo_dia": tipo_dia_real, "esperado": esperado_dia,
                        "bruto_dia": "--", "total_dia": "--", "saldo_dia_str": "--", "saldo_dia_positivo": True, 
                        "ajustado": ajustado, "auto_almoco": False, "atrasado": False, "almoco_longo": False, "aprovado": False, "tem_erro_original": False
                    })
                continue

            if inconsistente: err += 1
            else: ok_d += 1
                
            if len(batidas) >= 2 and batidas[0] >= "08:45:00": atr += 1
            if len(batidas) == 4 and (datetime.strptime(batidas[2][:5], "%H:%M") - datetime.strptime(batidas[1][:5], "%H:%M")).total_seconds() > 3600: est += 1
                
            saldo_d = liquido_dia_seg - esperado_dia
            detalhes_dias.append({
                "data": dt["data_formatada"], "data_raw": data_str, "batidas": [b[:5] for b in batidas], 
                "inconsistente": inconsistente, "falta": False, "tipo_dia": tipo_dia_real, "esperado": esperado_dia,
                "bruto_dia": bruto_str, "total_dia": liquido_str, 
                "saldo_dia_str": f"{'+' if saldo_d>=0 else '-'}{int(abs(saldo_d)//3600)}h {int((abs(saldo_d)%3600)//60):02d}m",
                "saldo_dia_positivo": saldo_d >= 0, "ajustado": ajustado, "auto_almoco": auto_almoco,
                "atrasado": (len(batidas) >= 2 and batidas[0] >= "08:45:00"), 
                "almoco_longo": (len(batidas) == 4 and (datetime.strptime(batidas[2][:5], "%H:%M") - datetime.strptime(batidas[1][:5], "%H:%M")).total_seconds() > 3600),
                "aprovado": is_aprovado, "tem_erro_original": tem_erro_original
            })
            
        saldo_seg = total_liquido_mes - esperado_mes
        percent = min(100, int((total_liquido_mes / esperado_mes) * 100)) if esperado_mes > 0 else (100 if total_liquido_mes > 0 else 0)
        
        relatorio.append({
            "nome": nome, "dias_trabalhados": ok_d, "dias_erro": err, "faltas": faltas,
            "atrasos_entrada": atr, "estouros_almoco": est,
            "total_bruto": f"{int(total_bruto_mes//3600)}h {int((total_bruto_mes%3600)//60):02d}m",
            "total_horas": f"{int(total_liquido_mes//3600)}h {int((total_liquido_mes%3600)//60):02d}m",
            "saldo_str": f"{'+' if saldo_seg>=0 else '-'} {int(abs(saldo_seg)//3600)}h {int((abs(saldo_seg)%3600)//60):02d}m",
            "saldo_positivo": saldo_seg >= 0, "percentual_regua": percent, "detalhes_dias": detalhes_dias
        })
        
    return sorted(relatorio, key=lambda x: x["nome"])

def obter_dicionario_ferias(db: Session):
    return {u.nome: {"inicio": getattr(u, "ferias_inicio", None), "fim": getattr(u, "ferias_fim", None)} for u in db.query(Usuario).all()}

# =====================================================================
# ROTAS DO SISTEMA DE PONTO ELETRÔNICO
# =====================================================================

@router.get("/administracao/relatorio-ponto-funcionarios", response_class=HTMLResponse)
async def relatorio_ponto_funcionarios(request: Request, usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    usuario_db = verificar_acesso("administracao", usuario_logado, db)
    if not usuario_db: return RedirectResponse(url="/dashboard", status_code=302)
    folhas = db.query(FolhaMensal).order_by(FolhaMensal.mes_ano.desc()).all()
    return templates.TemplateResponse(request=request, name="lista_meses_ponto.html", context={"usuario": usuario_db, "folhas": folhas})

@router.post("/api/admin/importar-ponto")
async def importar_ponto(arquivo_afd: UploadFile = File(...), usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    if not decodificar_token(usuario_logado): return RedirectResponse(url="/", status_code=302)
    conteudo = await arquivo_afd.read()
    conteudo_texto = conteudo.decode("utf-8", errors="ignore")
    
    padrao = re.search(r'\d{2}-(\d{2})-(\d{4})', arquivo_afd.filename)
    mes_num, ano = (padrao.group(1), padrao.group(2)) if padrao else (datetime.now().strftime("%m"), datetime.now().strftime("%Y"))
    mes_referencia = f"{ano}-{mes_num}"
    nome_exibicao = f"{mes_num} / {ano}"

    folha_existente = db.query(FolhaMensal).filter(FolhaMensal.mes_ano == mes_referencia).first()
    config_cal = json.loads(folha_existente.calendario_mes) if folha_existente and folha_existente.calendario_mes else {}
    excecoes = json.loads(folha_existente.excecoes_individuais) if folha_existente and folha_existente.excecoes_individuais else {}
    edicoes = json.loads(folha_existente.edicoes_manuais) if folha_existente and folha_existente.edicoes_manuais else {}
    
    ferias_dict = obter_dicionario_ferias(db)
    dados_calculados = calcular_relatorio_ponto(conteudo_texto, mes_referencia, config_cal, excecoes, edicoes, ferias_dict)
    
    if folha_existente:
        folha_existente.dados_consolidados = json.dumps(dados_calculados)
        folha_existente.arquivo_bruto = conteudo_texto
    else:
        db.add(FolhaMensal(mes_ano=mes_referencia, nome_exibicao=nome_exibicao, dados_consolidados=json.dumps(dados_calculados), arquivo_bruto=conteudo_texto))
        
    for rel in dados_calculados:
        func_db = db.query(Usuario).filter(Usuario.nome.ilike(f"%{rel['nome']}%")).first()
        if func_db:
            func_db.banco_horas = rel['saldo_str']
            func_db.espelho_ponto = json.dumps(rel)
    db.commit()
    return RedirectResponse(url=f"/administracao/ver-ponto/{mes_referencia}", status_code=303)

@router.get("/administracao/ver-ponto/{mes_ano}", response_class=HTMLResponse)
async def ver_ponto_mes(mes_ano: str, request: Request, usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    usuario_db = verificar_acesso("administracao", usuario_logado, db)
    if not usuario_db: return RedirectResponse(url="/dashboard", status_code=302)
        
    folha = db.query(FolhaMensal).filter(FolhaMensal.mes_ano == mes_ano).first()
    if not folha: return RedirectResponse(url="/administracao/relatorio-ponto-funcionarios", status_code=302)
    
    ano, mes = map(int, mes_ano.split("-"))
    lista_dias = [{"data_raw": f"{ano}-{mes:02d}-{d:02d}", "dia_num": d} for d in range(1, calendar.monthrange(ano, mes)[1] + 1)]
    return templates.TemplateResponse(request=request, name="relatorio_ponto.html", context={"usuario": usuario_db, "relatorio": json.loads(folha.dados_consolidados), "nome_arquivo": folha.nome_exibicao, "mes_ano": mes_ano, "lista_dias": lista_dias, "config_cal": json.loads(folha.calendario_mes) if folha.calendario_mes else {}})

@router.post("/api/admin/atualizar-calendario")
async def atualizar_calendario(request: Request, usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    if not verificar_acesso("administracao", usuario_logado, db): return {"status": "erro"}
    corpo = await request.json()
    mes_ano = corpo.get("mes_ano")
    novo_calendario = corpo.get("calendario")
    
    folha = db.query(FolhaMensal).filter(FolhaMensal.mes_ano == mes_ano).first()
    if not folha or not folha.arquivo_bruto: return {"status": "erro"}
    
    excecoes = json.loads(folha.excecoes_individuais) if folha.excecoes_individuais else {}
    edicoes = json.loads(folha.edicoes_manuais) if folha.edicoes_manuais else {}
    
    ferias_dict = obter_dicionario_ferias(db)
    dados_recalculados = calcular_relatorio_ponto(folha.arquivo_bruto, mes_ano, novo_calendario, excecoes, edicoes, ferias_dict)
    
    folha.calendario_mes = json.dumps(novo_calendario)
    folha.dados_consolidados = json.dumps(dados_recalculados)
    
    for rel in dados_recalculados:
        func_db = db.query(Usuario).filter(Usuario.nome.ilike(f"%{rel['nome']}%")).first()
        if func_db:
            func_db.banco_horas = rel['saldo_str']
            func_db.espelho_ponto = json.dumps(rel)
    db.commit()
    return {"status": "sucesso"}

@router.post("/api/admin/corrigir-ponto-massa")
async def corrigir_ponto_massa(request: Request, usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    if not verificar_acesso("administracao", usuario_logado, db): raise HTTPException(status_code=403, detail="Acesso negado")
    
    corpo = await request.json()
    nome_funcionario = corpo.get("nome_funcionario")
    mes_ano = corpo.get("mes_ano")
    dias = corpo.get("dias", [])
    
    folha = db.query(FolhaMensal).filter(FolhaMensal.mes_ano == mes_ano).first()
    edicoes = json.loads(folha.edicoes_manuais) if folha.edicoes_manuais else {}
    if nome_funcionario not in edicoes: edicoes[nome_funcionario] = {}
    
    excecoes = json.loads(folha.excecoes_individuais) if folha.excecoes_individuais else {}
    if nome_funcionario not in excecoes: excecoes[nome_funcionario] = {}
    
    for dia in dias:
        data_raw = dia.get("data_raw")
        b_list = [dia.get("b1"), dia.get("b2"), dia.get("b3"), dia.get("b4")]
        novas_batidas = [b.strip() for b in b_list if b and b.strip() and b.strip() != "--"]
        novas_batidas.sort()
        edicoes[nome_funcionario][data_raw] = novas_batidas
        
        if excecoes[nome_funcionario].get(data_raw) == "Aprovado":
            del excecoes[nome_funcionario][data_raw]
        
    folha.edicoes_manuais = json.dumps(edicoes)
    folha.excecoes_individuais = json.dumps(excecoes)
    
    config_cal = json.loads(folha.calendario_mes) if folha.calendario_mes else {}
    ferias_dict = obter_dicionario_ferias(db)
    
    dados_recalculados = calcular_relatorio_ponto(folha.arquivo_bruto, mes_ano, config_cal, excecoes, edicoes, ferias_dict)
    folha.dados_consolidados = json.dumps(dados_recalculados)
    
    for rel in dados_recalculados:
        func_db = db.query(Usuario).filter(Usuario.nome.ilike(f"%{rel['nome']}%")).first()
        if func_db:
            func_db.banco_horas = rel['saldo_str']
            func_db.espelho_ponto = json.dumps(rel)
            
    db.commit()
    return {"status": "sucesso"}

@router.post("/api/admin/alternar-folga")
async def alternar_folga(nome_funcionario: str = Form(...), data_raw: str = Form(...), mes_ano: str = Form(...), usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    if not verificar_acesso("administracao", usuario_logado, db): raise HTTPException(status_code=403, detail="Acesso negado")
    
    folha = db.query(FolhaMensal).filter(FolhaMensal.mes_ano == mes_ano).first()
    excecoes = json.loads(folha.excecoes_individuais) if folha.excecoes_individuais else {}
    if nome_funcionario not in excecoes: excecoes[nome_funcionario] = {}
    
    if excecoes[nome_funcionario].get(data_raw) == "Folga": del excecoes[nome_funcionario][data_raw]
    else: excecoes[nome_funcionario][data_raw] = "Folga"
        
    folha.excecoes_individuais = json.dumps(excecoes)
    
    config_cal = json.loads(folha.calendario_mes) if folha.calendario_mes else {}
    edicoes = json.loads(folha.edicoes_manuais) if folha.edicoes_manuais else {}
    ferias_dict = obter_dicionario_ferias(db)
    
    dados_recalculados = calcular_relatorio_ponto(folha.arquivo_bruto, mes_ano, config_cal, excecoes, edicoes, ferias_dict)
    folha.dados_consolidados = json.dumps(dados_recalculados)
    for rel in dados_recalculados:
        func_db = db.query(Usuario).filter(Usuario.nome.ilike(f"%{rel['nome']}%")).first()
        if func_db:
            func_db.banco_horas = rel['saldo_str']
            func_db.espelho_ponto = json.dumps(rel)
    db.commit()
    return {"status": "sucesso"}

@router.post("/api/admin/aprovar-dia")
async def aprovar_dia(nome_funcionario: str = Form(...), data_raw: str = Form(...), mes_ano: str = Form(...), usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    if not verificar_acesso("administracao", usuario_logado, db): raise HTTPException(status_code=403, detail="Acesso negado")
    
    folha = db.query(FolhaMensal).filter(FolhaMensal.mes_ano == mes_ano).first()
    excecoes = json.loads(folha.excecoes_individuais) if folha.excecoes_individuais else {}
    if nome_funcionario not in excecoes: excecoes[nome_funcionario] = {}
    
    if excecoes[nome_funcionario].get(data_raw) == "Aprovado": del excecoes[nome_funcionario][data_raw]
    else: excecoes[nome_funcionario][data_raw] = "Aprovado"
        
    folha.excecoes_individuais = json.dumps(excecoes)
    
    config_cal = json.loads(folha.calendario_mes) if folha.calendario_mes else {}
    edicoes = json.loads(folha.edicoes_manuais) if folha.edicoes_manuais else {}
    ferias_dict = obter_dicionario_ferias(db)
    
    dados_recalculados = calcular_relatorio_ponto(folha.arquivo_bruto, mes_ano, config_cal, excecoes, edicoes, ferias_dict)
    folha.dados_consolidados = json.dumps(dados_recalculados)
    db.commit()
    return {"status": "sucesso"}

@router.post("/api/admin/lancar-ferias")
async def lancar_ferias(nome_funcionario: str = Form(...), inicio: str = Form(""), fim: str = Form(""), mes_ano: str = Form(...), usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    if not verificar_acesso("administracao", usuario_logado, db): raise HTTPException(status_code=403)
    
    func_db = db.query(Usuario).filter(Usuario.nome.ilike(f"%{nome_funcionario}%")).first()
    if func_db:
        func_db.ferias_inicio = inicio if inicio else None
        func_db.ferias_fim = fim if fim else None
        
        folha = db.query(FolhaMensal).filter(FolhaMensal.mes_ano == mes_ano).first()
        if folha:
            config_cal = json.loads(folha.calendario_mes) if folha.calendario_mes else {}
            excecoes = json.loads(folha.excecoes_individuais) if folha.excecoes_individuais else {}
            edicoes = json.loads(folha.edicoes_manuais) if folha.edicoes_manuais else {}
            ferias_dict = obter_dicionario_ferias(db)
            
            dados_recalculados = calcular_relatorio_ponto(folha.arquivo_bruto, mes_ano, config_cal, excecoes, edicoes, ferias_dict)
            folha.dados_consolidados = json.dumps(dados_recalculados)
            for rel in dados_recalculados:
                f_db = db.query(Usuario).filter(Usuario.nome.ilike(f"%{rel['nome']}%")).first()
                if f_db:
                    f_db.banco_horas = rel['saldo_str']
                    f_db.espelho_ponto = json.dumps(rel)
        db.commit()
    return RedirectResponse(url=f"/administracao/ver-ponto/{mes_ano}", status_code=303)

@router.post("/api/admin/excluir-ponto")
async def excluir_ponto_mensal(mes_ano: str = Form(...), senha_admin: str = Form(...), usuario_logado: str = Cookie(None), db: Session = Depends(get_db)):
    usuario_adm = verificar_acesso("administracao", usuario_logado, db)
    if not usuario_adm: return {"status": "erro", "mensagem": "Acesso negado."}
    
    from passlib.context import CryptContext
    pwd_context_local = CryptContext(schemes=["bcrypt"], deprecated="auto")
    if not pwd_context_local.verify(senha_admin, usuario_adm.senha_hash):
        return {"status": "erro", "mensagem": "Senha incorreta!"}

    folha = db.query(FolhaMensal).filter(FolhaMensal.mes_ano == mes_ano).first()
    if folha:
        db.delete(folha)
        db.commit()
    pasta_destino = f"uploads/historico_pontos/{mes_ano}"
    if os.path.exists(pasta_destino): shutil.rmtree(pasta_destino)
    return {"status": "sucesso"}
# =========================================================
# SOLICITAR EXPLICAÇÃO DE PONTO AO FUNCIONÁRIO
# =========================================================
@router.post("/api/admin/pedir-explicacao")
async def pedir_explicacao_ponto(
    nome_funcionario: str = Form(...), data_raw: str = Form(...), mensagem: str = Form(...),
    usuario_logado: str = Cookie(None), db: Session = Depends(get_db)
):
    if not verificar_acesso("administracao", usuario_logado, db): raise HTTPException(status_code=403)
        
    # Normaliza o nome (remove espaços extras, deixa minúsculo)
    busca_limpa = " ".join(nome_funcionario.split()).lower()
    
    # Busca todos os usuários
    usuarios = db.query(Usuario).all()
    
    # Primeiro tenta o match exato (o nome do relógio é igual ao nome no banco)
    match_exato = [u for u in usuarios if " ".join(u.nome.split()).lower() == busca_limpa]
    
    if len(match_exato) == 1:
        func_db = match_exato[0]
    elif len(match_exato) > 1:
        # Se houver dois "Antonio" cadastrados, avisa o RH
        return {"status": "erro", "mensagem": f"Existem múltiplos funcionários cadastrados como '{nome_funcionario}'. Por favor, renomeie no cadastro para diferenciar (ex: Antonio Silva)."}
    else:
        # Se não for exato, tenta o match parcial. Mas se achar mais de um, avisa.
        match_parcial = [u for u in usuarios if busca_limpa in " ".join(u.nome.split()).lower() or " ".join(u.nome.split()).lower() in busca_limpa]
        
        if len(match_parcial) == 1:
            func_db = match_parcial[0]
        elif len(match_parcial) > 1:
            nomes = ", ".join([u.nome for u in match_parcial])
            return {"status": "erro", "mensagem": f"O nome '{nome_funcionario}' é ambíguo. Pode ser: {nomes}. Por favor, seja mais específico."}
        else:
            return {"status": "erro", "mensagem": f"Não foi possível localizar a conta do funcionário '{nome_funcionario}'."}
    
    # Se chegou aqui, temos exatamente 1 funcionário.
    msg_com_data = f"{mensagem} [DIA_ALVO:{data_raw}]"
    
    nova_notificacao = Notificacao(
        remetente="Recursos Humanos", destinatario_usuario=func_db.usuario,
        tipo="explicacao_ponto", mensagem=msg_com_data, lida=False
    )
    db.add(nova_notificacao)
    db.commit()
    return {"status": "sucesso"}

# =========================================================
# FUNCIONÁRIO: ENVIAR CORREÇÃO EXATA DE PONTO PARA O RH
# =========================================================
@router.post("/api/usuarios/justificar-ponto")
async def justificar_ponto(
    mes_ano: str = Form(...),
    data_raw: str = Form(...),
    data_texto: str = Form(...), 
    b1: str = Form(""), b2: str = Form(""), b3: str = Form(""), b4: str = Form(""),
    motivo: str = Form(...),
    usuario_logado: str = Cookie(None),
    db: Session = Depends(get_db)
):
    def _hora_valida(v: str) -> bool:
        if not v or v.strip() == "" or v.strip() == "--":
            return True
        return bool(re.match(r"^\d{2}:\d{2}$", v.strip()))

    for campo, nome in [(b1, "b1"), (b2, "b2"), (b3, "b3"), (b4, "b4")]:
        if not _hora_valida(campo):
            raise HTTPException(status_code=400, detail=f"Horário inválido no campo {nome}.")

    if not re.match(r"^\d{4}-\d{2}$", mes_ano):
        raise HTTPException(status_code=400, detail="Mês de referência inválido.")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", data_raw):
        raise HTTPException(status_code=400, detail="Data inválida.")
    
    username = decodificar_token(usuario_logado)
    if not username: raise HTTPException(status_code=401)
    
    usuario_db = db.query(Usuario).filter(Usuario.usuario == username).first()
    nome_completo = usuario_db.nome if usuario_db else username
    
    # 🧠 MÁGICA: O texto do RH fica bonito, mas o Python embute os dados ocultos no final!
    msg_texto = f"Correção de Ponto ({nome_completo}) - Dia {data_texto}\nBatidas: {b1 or '--'} | {b2 or '--'} | {b3 or '--'} | {b4 or '--'}\nMotivo: {motivo}\n[DADOS:{mes_ano}|{data_raw}|{b1}|{b2}|{b3}|{b4}]"
    
    nova_notificacao = Notificacao(
        remetente=username,
        destinatario_setor="administracao",
        tipo="acao",
        mensagem=msg_texto,
        lida=False
    )
    
    db.add(nova_notificacao)
    db.commit()
    return {"status": "sucesso"}