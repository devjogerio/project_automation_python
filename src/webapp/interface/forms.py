from django import forms


class SendTextForm(forms.Form):
    """Formulário para envio de texto via WAHA."""
    to = forms.CharField(label="Telefone (E.164 Brasil)", max_length=16)
    message = forms.CharField(label="Mensagem", widget=forms.Textarea, max_length=1000)


class SessionForm(forms.Form):
    """Formulário para operações de sessão WAHA."""
    name = forms.CharField(label="Nome da sessão", max_length=32)
    action = forms.ChoiceField(
        label="Ação",
        choices=[("create", "Criar"), ("start", "Iniciar"), ("status", "Status"), ("stop", "Parar")],
    )

