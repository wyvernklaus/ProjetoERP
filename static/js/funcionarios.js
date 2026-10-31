// ==========================================
// FUNÇÕES DE MODAL
// ==========================================
function abrirModal(id) { document.getElementById(id).classList.remove('hidden'); }
function fecharModal(id) { document.getElementById(id).classList.add('hidden'); }

function abrirModalEdicao(id, nome, usuario, email, cargo, abasPermitidas) {
    document.getElementById('edit_id').value = id;
    document.getElementById('edit_nome').value = nome;
    document.getElementById('edit_usuario').value = usuario;
    document.getElementById('edit_email').value = email === 'None' ? '' : email;
    document.getElementById('edit_cargo').value = cargo;
    
    const checkboxes = document.getElementById('edit_abas_container').querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(cb => cb.checked = false);
    
    if (abasPermitidas) {
        const abas = abasPermitidas.split(',');
        checkboxes.forEach(cb => { if (abas.includes(cb.value)) cb.checked = true; });
    } 
    abrirModal('modalEditarUsuario');
}

// ==========================================
// REQUISIÇÕES AJAX - GESTÃO AVANÇADA
// ==========================================

// 1. BLOQUEAR / DESBLOQUEAR
async function alterarBloqueio(idUsuario, botao) {
    const fd = new FormData(); fd.append("id_usuario", idUsuario);
    botao.innerText = "⏳...";
    
    const res = await fetch("/api/usuarios/bloquear", { method: "POST", body: fd });
    const dados = await res.json();
    
    if (dados.status === "sucesso") {
        const linha = document.getElementById(`linha-func-${idUsuario}`);
        const badge = document.getElementById(`status-badge-${idUsuario}`);
        
        if (dados.novo_status) {
            botao.innerText = "🚫 Bloquear";
            botao.className = "bg-gray-700 hover:bg-gray-600 text-amber-400 font-bold py-1 px-2.5 rounded text-xs transition shadow";
            badge.innerHTML = '<span class="bg-green-900 bg-opacity-30 text-green-400 border border-green-800 text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider">Ativo</span>';
            linha.classList.remove('opacity-50', 'bg-gray-900', 'bg-opacity-40');
        } else {
            botao.innerText = "✅ Desbloquear";
            botao.className = "bg-green-700 hover:bg-green-600 text-white font-bold py-1 px-2.5 rounded text-xs transition shadow";
            badge.innerHTML = '<span class="bg-red-900 bg-opacity-30 text-red-400 border border-red-800 text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider">Bloqueado</span>';
            linha.classList.add('opacity-50', 'bg-gray-900', 'bg-opacity-40');
        }
    }
}

// 2. EXCLUIR REGISTRO
async function excluirFuncionario(idUsuario, nomeFunc) {
    if (!confirm(`⚠️ ATENÇÃO: Tem certeza que deseja deletar permanentemente o cadastro de ${nomeFunc}? Esta ação não pode ser desfeita.`)) return;
    
    const fd = new FormData(); fd.append("id_usuario", idUsuario);
    const res = await fetch("/api/usuarios/excluir", { method: "POST", body: fd });
    const dados = await res.json();
    
    if (dados.status === "sucesso") {
        document.getElementById(`linha-func-${idUsuario}`).remove();
    } else {
        alert("Erro ao remover funcionário.");
    }
}

// 3. SOLICITAR RESET DE SENHA
async function solicitarResetSenha(idUsuario, botao) {
    const textoOriginal = botao.innerText;
    botao.innerText = "⚡ Enviando...";
    botao.disabled = true;
    
    const fd = new FormData(); fd.append("id_usuario", idUsuario);
    const res = await fetch("/api/usuarios/solicitar-reset-senha", { method: "POST", body: fd });
    const dados = await res.json();
    
    if (dados.status === "sucesso") {
        botao.innerText = "✉️ Link Gerado!";
        botao.className = "bg-green-600 text-white font-bold py-1 px-2 rounded text-xs transition shadow";
        setTimeout(() => {
            botao.innerText = textoOriginal;
            botao.className = "bg-purple-600 hover:bg-purple-500 text-white font-bold py-1 px-2 rounded text-xs transition shadow";
            botao.disabled = false;
        }, 3000);
    } else {
        alert(`❌ Erro: ${dados.mensagem}`);
        botao.innerText = textoOriginal;
        botao.disabled = false;
    }
}