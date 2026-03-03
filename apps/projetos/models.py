from django.db import models
from django.conf import settings


class Projeto(models.Model):
    STATUS_CHOICES = [
        ('rascunho', 'Rascunho'),
        ('planejamento', 'Planejamento'),
        ('execucao', 'Execução'),
        ('monitoramento', 'Monitoramento'),
        ('encerrado', 'Encerrado'),
        ('suspenso', 'Suspenso'),
    ]

    nome = models.CharField(max_length=300)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='rascunho')
    data_inicio = models.DateField(null=True, blank=True)
    gerente = models.CharField(max_length=200, blank=True)
    patrocinador = models.CharField(max_length=200, blank=True)
    encerrado = models.BooleanField(default=False)

    # JSON completo do projeto (TAP, EAP, Gantt, KPIs, Riscos etc.)
    dados = models.JSONField(default=dict)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Projeto'
        verbose_name_plural = 'Projetos'
        ordering = ['-criado_em']

    def __str__(self):
        return f"#{self.id} - {self.nome}"

    def get_tap(self):
        return self.dados.get('tap', {})

    def get_eap_tasks(self):
        return self.dados.get('eapTasks', [])

    def get_finances(self):
        return self.dados.get('finances', [])

    def get_kpis(self):
        return self.dados.get('kpis', [])

    def get_risks(self):
        return self.dados.get('risks', [])

    def get_action_plan(self):
        return self.dados.get('actionPlan', [])


class ProjetoAcesso(models.Model):
    """Controla quais clientes têm acesso a quais projetos."""
    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name='acessos')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='projetos_acesso')
    pode_ver_tap = models.BooleanField(default=True)
    pode_ver_eap = models.BooleanField(default=True)
    pode_ver_gantt = models.BooleanField(default=True)
    pode_ver_controle = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Acesso ao Projeto'
        verbose_name_plural = 'Acessos aos Projetos'
        unique_together = ('projeto', 'usuario')

    def __str__(self):
        return f"{self.usuario} → {self.projeto}"
