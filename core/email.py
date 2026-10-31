import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from core.config import settings

def enviar_email_background(destinatario: str, assunto: str, corpo_html: str):
    msg = MIMEMultipart()
    msg['From'] = f"Gestão ERP <{settings.EMAIL_REMETENTE}>"
    msg['To'] = destinatario
    msg['Subject'] = assunto
    msg.attach(MIMEText(corpo_html, 'html'))
    try:
        servidor = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=10)
        servidor.starttls()
        servidor.login(settings.EMAIL_REMETENTE, settings.EMAIL_SENHA_APP)
        servidor.send_message(msg)
        servidor.quit()
        print(f"📧 [SUCESSO] E-mail enviado para {destinatario}")
    except Exception as e:
        print(f"❌ [ERRO] Falha ao enviar e-mail para {destinatario}: {e}")