import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import Projeto, ProjetoAcesso


def get_projetos_usuario(user):
    """Retorna queryset de projetos acessíveis ao usuário."""
    if user.is_admin_erp:
        return Projeto.objects.all()
    ids = ProjetoAcesso.objects.filter(usuario=user).values_list('projeto_id', flat=True)
    return Projeto.objects.filter(id__in=ids)


def check_acesso(user, projeto):
    """Verifica se usuário tem acesso ao projeto. Lança Http404 se não."""
    if user.is_admin_erp:
        return True
    if not ProjetoAcesso.objects.filter(usuario=user, projeto=projeto).exists():
        raise Http404


@login_required
def lista(request):
    projetos = get_projetos_usuario(request.user)
    ativos = projetos.filter(encerrado=False)
    encerrados = projetos.filter(encerrado=True)
    return render(request, 'projetos/lista.html', {
        'projetos_ativos': ativos,
        'projetos_encerrados': encerrados,
    })


@login_required
def detalhe(request, pk):
    projeto = get_object_or_404(Projeto, pk=pk)
    check_acesso(request.user, projeto)

    acesso = None
    if not request.user.is_admin_erp:
        acesso = ProjetoAcesso.objects.filter(usuario=request.user, projeto=projeto).first()

    return render(request, 'projetos/detalhe.html', {
        'projeto': projeto,
        'acesso': acesso,
        'tap': projeto.get_tap(),
        'eap_tasks': json.dumps(projeto.get_eap_tasks()),
        'finances': json.dumps(projeto.get_finances()),
        'is_admin': request.user.is_admin_erp,
    })


# ── CRUD (apenas admin) ──────────────────────────────────

@login_required
def novo(request):
    if not request.user.is_admin_erp:
        raise Http404
    if request.method == 'POST':
        nome = request.POST.get('nome', 'Novo Projeto')
        status = request.POST.get('status', 'rascunho')
        data_inicio = request.POST.get('data_inicio') or None
        gerente = request.POST.get('gerente', '')
        patrocinador = request.POST.get('patrocinador', '')
        dados_iniciais = {
            'tap': {
                'nome': nome, 'status': status,
                'dataInicio': str(data_inicio) if data_inicio else '',
                'gerente': gerente, 'patrocinador': patrocinador,
                'objetivo': '', 'escopo': '', 'premissas': '',
                'requisitos': '', 'alteracoesEscopo': [],
            },
            'eapTasks': [], 'finances': [], 'kpis': [],
            'risks': [], 'lessons': [], 'close': {}, 'actionPlan': [],
        }
        p = Projeto.objects.create(
            nome=nome, status=status, data_inicio=data_inicio,
            gerente=gerente, patrocinador=patrocinador, dados=dados_iniciais,
        )
        messages.success(request, f'Projeto "{nome}" criado com sucesso!')
        return redirect('projetos:detalhe', pk=p.pk)
    return render(request, 'projetos/novo.html')


@login_required
def salvar_dados(request, pk):
    """API para salvar JSON completo do projeto (AJAX)."""
    if not request.user.is_admin_erp:
        return JsonResponse({'erro': 'Sem permissão'}, status=403)
    projeto = get_object_or_404(Projeto, pk=pk)
    try:
        dados = json.loads(request.body)
        projeto.dados = dados
        tap = dados.get('tap', {})
        projeto.nome = tap.get('nome', projeto.nome) or projeto.nome
        projeto.status = tap.get('status', projeto.status)
        projeto.gerente = tap.get('gerente', '')
        projeto.patrocinador = tap.get('patrocinador', '')
        data_str = tap.get('dataInicio', '')
        if data_str:
            from datetime import date
            try:
                projeto.data_inicio = date.fromisoformat(data_str)
            except Exception:
                pass
        projeto.save()
        return JsonResponse({'ok': True, 'nome': projeto.nome})
    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=400)


@login_required
def encerrar(request, pk):
    if not request.user.is_admin_erp:
        raise Http404
    projeto = get_object_or_404(Projeto, pk=pk)
    projeto.encerrado = True
    projeto.status = 'encerrado'
    projeto.save()
    messages.success(request, f'Projeto "{projeto.nome}" encerrado.')
    return redirect('projetos:lista')


@login_required
def reabrir(request, pk):
    if not request.user.is_admin_erp:
        raise Http404
    projeto = get_object_or_404(Projeto, pk=pk)
    projeto.encerrado = False
    projeto.status = 'execucao'
    projeto.save()
    messages.success(request, f'Projeto "{projeto.nome}" reaberto.')
    return redirect('projetos:lista')


@login_required
def excluir(request, pk):
    if not request.user.is_admin_erp:
        raise Http404
    projeto = get_object_or_404(Projeto, pk=pk)
    nome = projeto.nome
    projeto.delete()
    messages.success(request, f'Projeto "{nome}" excluído.')
    return redirect('projetos:lista')


@login_required
def gerenciar_acessos(request, pk):
    """Tela para liberar/revogar acesso de clientes ao projeto."""
    if not request.user.is_admin_erp:
        raise Http404
    from apps.accounts.models import User
    projeto = get_object_or_404(Projeto, pk=pk)
    clientes = User.objects.filter(perfil='cliente', is_active=True)
    acessos = {a.usuario_id: a for a in ProjetoAcesso.objects.filter(projeto=projeto)}

    if request.method == 'POST':
        usuarios_ids = request.POST.getlist('usuarios')
        # Remove acessos não selecionados
        ProjetoAcesso.objects.filter(projeto=projeto).exclude(usuario_id__in=usuarios_ids).delete()
        # Cria novos acessos
        for uid in usuarios_ids:
            ProjetoAcesso.objects.get_or_create(projeto=projeto, usuario_id=uid)
        messages.success(request, 'Acessos atualizados!')
        return redirect('projetos:detalhe', pk=pk)

    return render(request, 'projetos/acessos.html', {
        'projeto': projeto,
        'clientes': clientes,
        'acessos': acessos,
    })
