from core.database import SessionLocal, engine, Base
from core.modelos import Usuario, CncMaterial, Maquina
from passlib.context import CryptContext
import os

def configurar_banco_inicial():
    print("🛠️ Iniciando a configuração do banco de dados...")
    
    # 1. Cria todas as tabelas baseadas no modelos.py
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    try:
        # ==========================================
        # 2. CRIAR O USUÁRIO ADMINISTRADOR
        # ==========================================
        admin_existente = db.query(Usuario).filter(Usuario.usuario == "admin").first()
        if not admin_existente:
            senha_inicial = os.environ.get("ADMIN_SENHA_INICIAL")
            if not senha_inicial:
                print("⚠️ Nenhum usuário admin encontrado e a senha inicial não foi definida.")
                print("   PowerShell: $env:ADMIN_SENHA_INICIAL='sua_senha_forte'")
                print("   CMD:        set ADMIN_SENHA_INICIAL=sua_senha_forte")
                print("   Depois rode 'python setup_banco.py' novamente.")
                return
            print("👤 Criando o usuário Gerente (Admin)...")
            senha_criptografada = pwd_context.hash(senha_inicial)
            novo_usuario = Usuario(
                nome="Gerente",
                usuario="admin",
                email="",
                senha_hash=senha_criptografada,
                cargo="Gerente Geral",
                abas_permitidas="comercial,administracao,producao,operacional,manutencao_ti,config,gerencia"
            )
            db.add(novo_usuario)
            db.commit()
            print("✅ Usuário admin criado! Login: admin | Senha: a definida em ADMIN_SENHA_INICIAL")
        else:
            print("⚠️ Usuário 'admin' já existe. Pulando...")

        # ==========================================
        # 3. CADASTRAR MATERIAIS CNC (Biblioteca)
        # ==========================================
        materiais_manuais = [
            "Acrílico", "MDF", "ACM", "Alumínio", "Latão", "Madeira Maciça",
            "PVC Expandido", "PS", "Polipropileno", "XPS", "EPS", "Policarbonato",
            "Compensado Comum", "Balsa", "Bambu", "Tecidos", "Couro", "Papelão", "PETG", "EVA"
        ]
        
        novos_materiais = 0
        for mat in materiais_manuais:
            if not db.query(CncMaterial).filter(CncMaterial.nome == mat).first():
                db.add(CncMaterial(nome=mat, espessura_padrao=3.0))
                novos_materiais += 1
        db.commit()
        if novos_materiais > 0:
            print(f"📦 {novos_materiais} materiais CNC injetados.")
        else:
            print("⚠️ Materiais CNC já cadastrados. Pulando...")

        # ==========================================
        # 4. CADASTRAR MÁQUINAS PADRÃO
        # ==========================================
        # Router CNC
        router = db.query(Maquina).filter(Maquina.nome.like("%Router%")).first()
        if not router:
            print("🚜 Cadastrando a Router CNC...")
            router = Maquina(nome="Router CNC RMC", setor="operacional", status="Livre")
            db.add(router)
            db.commit()

        router.tamanho_util = "Não especificado"
        router.materiais_permitidos = "Alumínio, Latão, ACM, Acrílico, MDF, Madeira Maciça, PVC Expandido, PS, Polipropileno, XPS, EPS, Policarbonato"
        router.materiais_proibidos = "Vidro, Aço Carbono, Inox, Cerâmica"
        router.velocidade_corte = """Alumínio/Latão: Chipload 0.05-0.12mm
ACM: Chipload 0.15-0.25mm
Acrílico: Chipload 0.07-0.15mm
MDF/Madeira: Chipload 0.10-0.20mm"""
        db.commit()

        # Laser
        laser = db.query(Maquina).filter(Maquina.nome.like("%Laser%")).first()
        if not laser:
            print("⚡ Cadastrando a Laser GLC 1290...")
            laser = Maquina(nome="Laser GLC 1290", setor="operacional", status="Livre")
            db.add(laser)
            db.commit()

        laser.tamanho_util = "120 x 90 cm"
        laser.materiais_permitidos = "Acrílico, MDF, Compensado Comum, Balsa, Madeira Maciça, Bambu, Tecidos, Couro, Papelão, Papel, Polipropileno, PETG, EVA"
        laser.materiais_proibidos = "PVC, Vinil, Teflon, Policarbonato, ABS, Fibra de carbono, Fibra de vidro"
        laser.velocidade_corte = "Potência Recomendada: 15% a 80%"
        db.commit()
        
        print("✅ Máquinas configuradas com sucesso!")

    except Exception as e:
        print(f"❌ Erro ao configurar banco: {e}")
        db.rollback()
    finally:
        db.close()
        print("🏁 Configuração finalizada. Pode iniciar o 'python main.py'.")

if __name__ == "__main__":
    configurar_banco_inicial()