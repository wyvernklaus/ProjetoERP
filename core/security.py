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


# =========================================================
# SANITIZAÇÃO DE HTML (proteção contra XSS armazenado)
# Permite apenas tags/atributos seguros no campo "detalhes".
# =========================================================
from html import escape
from html.parser import HTMLParser

TAGS_PERMITIDAS = {"br", "hr", "b", "i", "strong", "em", "p", "div", "span", "u", "ul", "ol", "li", "img"}
ATRIBUTOS_PERMITIDOS = {"img": {"src"}}


class _SanitizadorHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self._saida = []

    def handle_starttag(self, tag, attrs):
        if tag in TAGS_PERMITIDAS:
            permitidos = ATRIBUTOS_PERMITIDOS.get(tag, set())
            attr_safe = []
            for k, v in attrs:
                if k not in permitidos:
                    continue
                if k == "src":
                    valor = (v or "").strip().lower()
                    if not valor.startswith(("http://", "https://", "data:image/")):
                        continue
                attr_safe.append(f' {k}="{escape(v, quote=True)}"')
            self._saida.append(f"<{tag}{''.join(attr_safe)}>")
        else:
            self._saida.append(escape(self.get_starttag_text() or f"<{tag}>"))

    def handle_endtag(self, tag):
        if tag in TAGS_PERMITIDAS:
            self._saida.append(f"</{tag}>")
        else:
            self._saida.append(escape(f"</{tag}>"))

    def handle_data(self, data):
        self._saida.append(escape(data))

    def handle_entityref(self, name):
        self._saida.append(f"&{name};")

    def handle_charref(self, name):
        self._saida.append(f"&#{name};")


def sanitizar_html(texto) -> str:
    """Remove scripts e atributos perigosos, mantendo formatação básica."""
    if not texto:
        return ""
    s = _SanitizadorHTML()
    s.feed(str(texto))
    return "".join(s._saida)