from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from .models import Section, Spot, TermoCompromisso
from .forms import SectionForm, SpotForm, TermoCompromissoForm
from django.core.exceptions import ValidationError
from django.db.models import Count, Q, Sum
from datetime import datetime, timedelta
from django.contrib.auth.mixins import LoginRequiredMixin
from contas.mixins import GroupRequiredMixin
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO
from django.conf import settings
import base64
import os
from django.db import models

# Create your views here.

# Views para Seções
class SectionListView(LoginRequiredMixin, ListView):
    model = Section
    template_name = 'secoes/section_list.html'
    context_object_name = 'sections'

class SectionCreateView(LoginRequiredMixin, GroupRequiredMixin, CreateView):
    model = Section
    form_class = SectionForm
    template_name = 'secoes/section_form.html'
    success_url = reverse_lazy('secoes:section_list')
    allowed_groups = ['admin', 'digitador']

    def form_valid(self, form):
        messages.success(self.request, 'Seção criada com sucesso!')
        return super().form_valid(form)

class SectionUpdateView(LoginRequiredMixin, GroupRequiredMixin, UpdateView):
    model = Section
    form_class = SectionForm
    template_name = 'secoes/section_form.html'
    success_url = reverse_lazy('secoes:section_list')
    allowed_groups = ['admin', 'digitador']

    def form_valid(self, form):
        messages.success(self.request, 'Seção atualizada com sucesso!')
        return super().form_valid(form)

class SectionDeleteView(LoginRequiredMixin, GroupRequiredMixin, DeleteView):
    model = Section
    template_name = 'secoes/section_confirm_delete.html'
    success_url = reverse_lazy('secoes:section_list')
    allowed_groups = ['admin', 'digitador']

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Seção excluída com sucesso!')
        return super().delete(request, *args, **kwargs)

# Views para Vagas
class SpotListView(LoginRequiredMixin, ListView):
    model = Spot
    template_name = 'secoes/spot_list.html'
    context_object_name = 'spots'

    def get_queryset(self):
        # Verificar se deve mostrar vagas inativas
        mostrar_inativas = self.request.GET.get('mostrar_inativas') == 'true'
        
        if mostrar_inativas:
            queryset = Spot.objects.all()  # Mostrar todas as vagas
        else:
            queryset = Spot.objects.filter(ativo=True)  # Filtrar apenas vagas ativas
            
        # Filtro por seção
        secao_id = self.request.GET.get('secao')
        if secao_id:
            queryset = queryset.filter(secao_id=secao_id)
        
        # Filtro por pesquisa (placa ou nome do militar)
        pesquisa = self.request.GET.get('pesquisa')
        if pesquisa:
            queryset = queryset.filter(
                models.Q(nome_bombeiro__icontains=pesquisa) |
                models.Q(placa_veiculo__icontains=pesquisa) |
                models.Q(placa_veiculo_adicional__icontains=pesquisa) |
                models.Q(placa_moto__icontains=pesquisa) |
                models.Q(matricula_bombeiro__icontains=pesquisa) |
                models.Q(cpf_bombeiro__icontains=pesquisa)
            )
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sections'] = Section.objects.all()
        context['mostrar_inativas'] = self.request.GET.get('mostrar_inativas') == 'true'
        context['pesquisa'] = self.request.GET.get('pesquisa', '')
        return context

class SpotCreateView(LoginRequiredMixin, GroupRequiredMixin, CreateView):
    model = Spot
    form_class = SpotForm
    template_name = 'secoes/spot_form.html'
    success_url = reverse_lazy('secoes:spot_list')
    allowed_groups = ['admin', 'digitador']

    def form_valid(self, form):
        # Verificar se há vagas disponíveis na seção
        secao = form.cleaned_data['secao']
        tipo_cobertura = form.cleaned_data['tipo_cobertura']
        nominada = form.cleaned_data['nominada']
        
        # Contar vagas existentes do mesmo tipo (apenas vagas ativas)
        vagas_existentes = Spot.objects.filter(
            secao=secao,
            tipo_cobertura=tipo_cobertura,
            nominada=nominada,
            ativo=True  # Apenas vagas ativas
        ).count()
        
        # Verificar limite baseado no tipo
        if tipo_cobertura == 'coberta' and nominada == 'nominada':
            limite = secao.vagas_cobertas_nominadas
        elif tipo_cobertura == 'coberta' and nominada == 'nao_nominada':
            limite = secao.vagas_cobertas_nao_nominadas
        elif tipo_cobertura == 'descoberta' and nominada == 'nominada':
            limite = secao.vagas_descobertas_nominadas
        else:  # descoberta e não nominada
            limite = secao.vagas_descobertas_nao_nominadas
        
        if vagas_existentes >= limite:
            messages.error(self.request, f'Não é possível criar mais vagas deste tipo. Limite atingido: {limite}')
            return self.form_invalid(form)
        
        # Validar o modelo antes de salvar
        try:
            form.instance.full_clean()
        except ValidationError as e:
            for field, errors in e.message_dict.items():
                for error in errors:
                    messages.error(self.request, f'{field}: {error}')
            return self.form_invalid(form)
        
        messages.success(self.request, 'Vaga criada com sucesso!')
        return super().form_valid(form)

class SpotUpdateView(LoginRequiredMixin, GroupRequiredMixin, UpdateView):
    model = Spot
    form_class = SpotForm
    template_name = 'secoes/spot_form.html'
    success_url = reverse_lazy('secoes:spot_list')
    allowed_groups = ['admin', 'digitador']

    def form_valid(self, form):
        # Validar o modelo antes de salvar
        try:
            form.instance.full_clean()
        except ValidationError as e:
            for field, errors in e.message_dict.items():
                for error in errors:
                    messages.error(self.request, f'{field}: {error}')
            return self.form_invalid(form)
        
        messages.success(self.request, 'Vaga atualizada com sucesso!')
        return super().form_valid(form)

class SpotDeleteView(LoginRequiredMixin, GroupRequiredMixin, DeleteView):
    model = Spot
    template_name = 'secoes/spot_confirm_delete.html'
    success_url = reverse_lazy('secoes:spot_list')
    allowed_groups = ['admin', 'digitador']

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Vaga excluída com sucesso!')
        return super().delete(request, *args, **kwargs)

class SpotDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'secoes/spot_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        spot = get_object_or_404(Spot, pk=self.kwargs['pk'])
        context['spot'] = spot
        return context

# Dashboard View
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'secoes/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estatísticas gerais
        total_secoes = Section.objects.count()
        total_vagas = Spot.objects.count()
        vagas_ocupadas = Spot.objects.filter(status='ocupada').count()
        
        # Vagas configuradas a partir das seções
        section_aggregates = Section.objects.aggregate(
            sum_vcn=Sum('vagas_cobertas_nominadas'),
            sum_vcnn=Sum('vagas_cobertas_nao_nominadas'),
            sum_vdn=Sum('vagas_descobertas_nominadas'),
            sum_vdnn=Sum('vagas_descobertas_nao_nominadas')
        )
        
        vagas_configuradas_cobertas_nominadas = section_aggregates.get('sum_vcn') or 0
        vagas_configuradas_cobertas_nao_nominadas = section_aggregates.get('sum_vcnn') or 0
        vagas_configuradas_descobertas_nominadas = section_aggregates.get('sum_vdn') or 0
        vagas_configuradas_descobertas_nao_nominadas = section_aggregates.get('sum_vdnn') or 0
        
        vagas_configuradas = (vagas_configuradas_cobertas_nominadas +
                              vagas_configuradas_cobertas_nao_nominadas +
                              vagas_configuradas_descobertas_nominadas +
                              vagas_configuradas_descobertas_nao_nominadas)
        
        # Vagas disponíveis
        vagas_disponiveis = vagas_configuradas - vagas_ocupadas
        
        # Estatísticas por tipo de vaga (baseado na configuração das seções)
        vagas_cobertas = vagas_configuradas_cobertas_nominadas + vagas_configuradas_cobertas_nao_nominadas
        vagas_descobertas = vagas_configuradas_descobertas_nominadas + vagas_configuradas_descobertas_nao_nominadas
        vagas_nominadas = vagas_configuradas_cobertas_nominadas + vagas_configuradas_descobertas_nominadas
        vagas_nao_nominadas = vagas_configuradas_cobertas_nao_nominadas + vagas_configuradas_descobertas_nao_nominadas
        
        # Vagas ocupadas por tipo
        vagas_cobertas_ocupadas = Spot.objects.filter(tipo_cobertura='coberta', status='ocupada').count()
        vagas_descobertas_ocupadas = Spot.objects.filter(tipo_cobertura='descoberta', status='ocupada').count()
        vagas_nominadas_ocupadas = Spot.objects.filter(nominada='nominada', status='ocupada').count()
        vagas_nao_nominadas_ocupadas = Spot.objects.filter(nominada='nao_nominada', status='ocupada').count()

        # Percentual de utilização geral
        percentual_utilizacao_geral = (vagas_ocupadas / vagas_configuradas * 100) if vagas_configuradas > 0 else 0
        
        # Outras estatísticas
        def get_perc(part, total):
            return (part / total * 100) if total > 0 else 0
        
        # Seções com mais vagas ocupadas
        secoes_mais_ocupadas = Section.objects.annotate(
            vagas_ocupadas=Count('vagas', filter=Q(vagas__status='ocupada'))
        ).order_by('-vagas_ocupadas')[:5]
        
        # Vagas ocupadas recentemente (últimos 7 dias)
        data_limite = datetime.now() - timedelta(days=7)
        vagas_ocupadas_recentes = Spot.objects.filter(
            status='ocupada',
            data_ocupacao__gte=data_limite
        ).count()
        
        # Vagas liberadas recentemente (últimos 7 dias)
        vagas_liberadas_recentes = Spot.objects.filter(
            status='livre'
        ).count()
        
        context.update({
            'total_secoes': total_secoes,
            'total_vagas': total_vagas,
            'vagas_ocupadas': vagas_ocupadas,
            'vagas_disponiveis': vagas_disponiveis,
            'vagas_configuradas': vagas_configuradas,
            'percentual_utilizacao_geral': round(percentual_utilizacao_geral, 1),
            
            # Estatísticas por tipo
            'vagas_cobertas': vagas_cobertas,
            'vagas_descobertas': vagas_descobertas,
            'vagas_nominadas': vagas_nominadas,
            'vagas_nao_nominadas': vagas_nao_nominadas,
            'vagas_cobertas_ocupadas': vagas_cobertas_ocupadas,
            'vagas_descobertas_ocupadas': vagas_descobertas_ocupadas,
            'vagas_nominadas_ocupadas': vagas_nominadas_ocupadas,
            'vagas_nao_nominadas_ocupadas': vagas_nao_nominadas_ocupadas,
            
            # Percentuais
            'perc_cobertas': round(get_perc(vagas_cobertas_ocupadas, vagas_cobertas), 1),
            'perc_descobertas': round(get_perc(vagas_descobertas_ocupadas, vagas_descobertas), 1),
            'perc_nominadas': round(get_perc(vagas_nominadas_ocupadas, vagas_nominadas), 1),
            'perc_nao_nominadas': round(get_perc(vagas_nao_nominadas_ocupadas, vagas_nao_nominadas), 1),
            
            # Dados para gráficos
            'secoes_mais_ocupadas': secoes_mais_ocupadas,
            'vagas_ocupadas_recentes': vagas_ocupadas_recentes,
            'vagas_liberadas_recentes': vagas_liberadas_recentes,
        })
        
        return context

@login_required
def liberar_vaga(request, spot_id):
    spot = get_object_or_404(Spot, pk=spot_id)
    
    if request.method == 'POST':
        # Limpar dados do bombeiro
        spot.nome_bombeiro = None
        spot.posto_bombeiro = None
        spot.matricula_bombeiro = None
        spot.cpf_bombeiro = None
        spot.telefone_bombeiro = None
        spot.email_bombeiro = None
        
        # Limpar dados dos veículos
        spot.placa_veiculo = None
        spot.modelo_veiculo = None
        spot.marca_veiculo = None
        spot.cor_veiculo = None
        spot.ano_veiculo = None
        spot.tipo_veiculo = None
        
        spot.placa_veiculo_adicional = None
        spot.modelo_veiculo_adicional = None
        spot.marca_veiculo_adicional = None
        spot.cor_veiculo_adicional = None
        spot.ano_veiculo_adicional = None
        spot.tipo_veiculo_adicional = None
        
        spot.placa_moto = None
        spot.modelo_moto = None
        spot.marca_moto = None
        spot.cor_moto = None
        spot.ano_moto = None
        
        # Marcar como livre e definir data de saída
        spot.status = 'livre'
        spot.data_saida = datetime.now()
        
        spot.save()
        
        messages.success(request, f'Vaga {spot.identificador or spot.pk} liberada com sucesso!')
        return redirect('secoes:spot_list')
    
    return render(request, 'secoes/liberar_vaga_confirm.html', {'spot': spot})

@login_required
def desativar_vaga(request, spot_id):
    spot = get_object_or_404(Spot, pk=spot_id)
    
    if request.method == 'POST':
        spot.ativo = False
        spot.save()
        messages.success(request, f'Vaga {spot.identificador or spot.pk} desativada com sucesso!')
        return redirect('secoes:spot_list')
    
    return render(request, 'secoes/desativar_vaga_confirm.html', {'spot': spot})

@login_required
def transferir_vaga(request, spot_id):
    spot = get_object_or_404(Spot, pk=spot_id)
    
    if request.method == 'POST':
        # Obter dados do formulário
        nova_secao_id = request.POST.get('nova_secao')
        novo_identificador = request.POST.get('novo_identificador', '').strip()
        
        if nova_secao_id:
            nova_secao = get_object_or_404(Section, pk=nova_secao_id)
            
            # Verificar se o novo identificador já existe na nova seção
            if novo_identificador:
                vaga_existente = Spot.objects.filter(
                    secao=nova_secao,
                    identificador=novo_identificador,
                    ativo=True
                ).exclude(pk=spot.pk)
                
                if vaga_existente.exists():
                    messages.error(request, f'Já existe uma vaga com o identificador "{novo_identificador}" na seção {nova_secao.nome}.')
                    return render(request, 'secoes/transferir_vaga.html', {
                        'spot': spot,
                        'sections': Section.objects.all()
                    })
            
            # Realizar a transferência
            spot.secao = nova_secao
            if novo_identificador:
                spot.identificador = novo_identificador
            spot.save()
            
            messages.success(request, f'Vaga transferida com sucesso para {nova_secao.nome}!')
            return redirect('secoes:spot_detail', pk=spot.pk)
        else:
            messages.error(request, 'Selecione uma seção para transferir a vaga.')
    
    return render(request, 'secoes/transferir_vaga.html', {
        'spot': spot,
        'sections': Section.objects.all()
    })

@login_required
def historico_vagas(request):
    """Lista o histórico de vagas transferidas e desativadas"""
    # Buscar vagas inativas (histórico)
    vagas_historico = Spot.objects.filter(
        ativo=False
    ).select_related('secao').order_by('-data_saida', '-data_ocupacao')
    
    # Filtrar por seção se especificado
    secao_id = request.GET.get('secao')
    if secao_id:
        vagas_historico = vagas_historico.filter(secao_id=secao_id)
    
    # Filtrar por tipo de histórico
    tipo_historico = request.GET.get('tipo')
    if tipo_historico == 'transferidas':
        # Vagas que foram transferidas (têm dados do bombeiro)
        vagas_historico = vagas_historico.filter(nome_bombeiro__isnull=False)
    elif tipo_historico == 'desativadas':
        # Vagas que foram desativadas (não têm dados do bombeiro)
        vagas_historico = vagas_historico.filter(nome_bombeiro__isnull=True)
    
    # Filtrar por data de saída
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    if data_inicio:
        vagas_historico = vagas_historico.filter(data_saida__date__gte=data_inicio)
    
    if data_fim:
        vagas_historico = vagas_historico.filter(data_saida__date__lte=data_fim)
    
    # Estatísticas
    total_historico = vagas_historico.count()
    vagas_transferidas = vagas_historico.filter(nome_bombeiro__isnull=False).count()
    vagas_desativadas = vagas_historico.filter(nome_bombeiro__isnull=True).count()
    
    context = {
        'vagas_historico': vagas_historico,
        'sections': Section.objects.all(),
        'total_historico': total_historico,
        'vagas_transferidas': vagas_transferidas,
        'vagas_desativadas': vagas_desativadas,
        'secao_filtro': secao_id,
        'tipo_filtro': tipo_historico,
    }
    
    return render(request, 'secoes/historico_vagas.html', context)

@login_required
def gerar_termo_compromisso(request, spot_id):
    """Gera o termo de compromisso em PDF para uma vaga específica"""
    spot = get_object_or_404(Spot, pk=spot_id)
    
    # Verificar se a vaga tem dados do bombeiro
    if not spot.nome_bombeiro:
        messages.error(request, 'Não é possível gerar o termo de compromisso para uma vaga sem dados do bombeiro.')
        return redirect('secoes:spot_list')
    
    # Função para converter data para extenso
    def data_por_extenso(data_str):
        from datetime import datetime
        meses = [
            'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
            'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'
        ]
        data = datetime.strptime(data_str, '%d/%m/%Y')
        return f"{data.day} de {meses[data.month - 1]} de {data.year}"
    
    # Carregar logo em base64
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'cbmepi_logo.png')
    with open(logo_path, 'rb') as logo_file:
        logo_base64 = base64.b64encode(logo_file.read()).decode()
    
    # Dados para o template
    data_atual = datetime.now().strftime('%d/%m/%Y')
    context = {
        'spot': spot,
        'data_atual': data_atual,
        'data_atual_extenso': data_por_extenso(data_atual),
        'hora_atual': datetime.now().strftime('%H:%M'),
        'logo_base64': logo_base64,
    }
    
    # Renderizar o template HTML
    template = get_template('secoes/termo_compromisso.html')
    html = template.render(context)
    
    # Criar o PDF
    result = BytesIO()
    pdf = pisa.CreatePDF(html, result)
    
    if not pdf.err:
        # Configurar a resposta HTTP para abrir inline
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="termo_compromisso_{spot.identificador}.pdf"'
        return response
    
    return HttpResponse('Erro ao gerar PDF', status=500)

@login_required
def gerar_lista_vagas(request):
    """Gera a lista completa de vagas com dados dos militares, seções e veículos"""
    # Buscar todas as vagas ocupadas com dados completos
    vagas = Spot.objects.filter(
        status='ocupada'
    ).select_related('secao').order_by('secao__nome', 'nome_bombeiro')
    
    # Buscar logo em base64 de forma robusta para dev e prod
    logo_base64 = ""
    logo_filename = 'cbmepi_logo.png'

    # Tenta encontrar a logo nos diretórios de staticfiles
    logo_path = None
    if hasattr(settings, 'STATICFILES_DIRS'):
        for static_dir in settings.STATICFILES_DIRS:
            possible_path = os.path.join(static_dir, logo_filename)
            if os.path.exists(possible_path):
                logo_path = possible_path
                break

    # Se não achou, tenta na pasta static do projeto
    if not logo_path:
        logo_path = os.path.join(settings.BASE_DIR, 'static', logo_filename)
        if not os.path.exists(logo_path):
            logo_path = None

    if logo_path:
        with open(logo_path, 'rb') as logo_file:
            logo_base64 = base64.b64encode(logo_file.read()).decode('utf-8')
    
    # Dados para o template
    context = {
        'vagas': vagas,
        'data_atual': datetime.now().strftime('%d/%m/%Y'),
        'hora_atual': datetime.now().strftime('%H:%M'),
        'total_vagas': vagas.count(),
        'logo_base64': logo_base64,
    }
    
    # Renderizar o template HTML
    template = get_template('secoes/lista_vagas.html')
    html = template.render(context)
    
    # Criar o PDF
    result = BytesIO()
    pdf = pisa.CreatePDF(html, result)
    
    if not pdf.err:
        # Configurar a resposta HTTP para abrir inline
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="lista_vagas_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf"'
        return response
    
    return HttpResponse('Erro ao gerar PDF', status=500)

@login_required
def upload_termo_compromisso_vaga(request, spot_id):
    """Upload do termo de compromisso assinado para uma vaga específica"""
    spot = get_object_or_404(Spot, pk=spot_id)
    
    if request.method == 'POST':
        form = TermoCompromissoForm(request.POST, request.FILES)
        if form.is_valid():
            termo = form.save(commit=False)
            termo.spot = spot
            termo.save()
            messages.success(request, f'Termo de Compromisso {termo.numero_documento} enviado com sucesso!')
            return redirect('secoes:spot_list')
    else:
        form = TermoCompromissoForm()
    
    # Buscar todos os termos existentes para esta vaga
    termos_existentes = spot.termos_compromisso.all()
    
    return render(request, 'secoes/upload_termo_vaga.html', {
        'form': form,
        'spot': spot,
        'termos_existentes': termos_existentes
    })
