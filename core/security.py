from collections import defaultdict
from time import time

# Estado em memória. Se virar multi-instância, troca por Redis.
_tentativas_login: dict[str, list[float]] = defaultdict(list)

LIMITE_TENTATIVAS = 5
JANELA_SEGUNDOS = 300  # 5 minutos

def verificar_rate_limit(chave: str) -> bool:
    """Retorna True se pode tentar, False se está bloqueado."""
    agora = time()
    tentativas = _tentativas_login[chave]
    tentativas[:] = [t for t in tentativas if agora - t < JANELA_SEGUNDOS]
    if len(tentativas) >= LIMITE_TENTATIVAS:
        return False
    tentativas.append(agora)
    return True

def resetar_rate_limit(chave: str) -> None:
    _tentativas_login.pop(chave, None)