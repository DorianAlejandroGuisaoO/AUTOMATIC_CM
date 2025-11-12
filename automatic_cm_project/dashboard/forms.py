from django import forms

class CreatePostForm(forms.Form):
    POST_TYPE_CHOICES = [
        ('text', 'Texto'),
        ('link', 'Enlace'),
        ('image', 'Imagen'),
    ]
    
    title = forms.CharField(
        max_length=300,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Título del post (máx. 300 caracteres)',
            'required': True
        }),
        label='Título'
    )
    
    post_type = forms.ChoiceField(
        choices=POST_TYPE_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'form-radio'
        }),
        initial='text',
        label='Tipo de post'
    )
    
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'Contenido del post, URL del enlace, o descripción de la imagen',
            'rows': 10
        }),
        label='Contenido',
        required=False
    )
    
    image = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-file-input',
            'accept': 'image/*'
        }),
        label='Imagen'
    )
    
    subreddit = forms.CharField(
        max_length=100,
        initial='ACM_Magneto',
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'readonly': True
        }),
        label='Subreddit'
    )


class GenerateJobPostForm(forms.Form):
    JOB_TYPE_CHOICES = [
        ('full_time', 'Tiempo Completo'),
        ('part_time', 'Medio Tiempo'),
        ('contract', 'Contrato'),
        ('temporary', 'Temporal'),
        ('internship', 'Práctica/Pasantía'),
    ]
    
    job_title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'ej: Desarrollador Python Senior',
        }),
        label='Título del puesto'
    )
    
    company_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'ej: Magneto Empleos',
        }),
        label='Nombre de la empresa'
    )
    
    job_type = forms.ChoiceField(
        choices=JOB_TYPE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Tipo de empleo'
    )
    
    location = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'ej: Medellín, Colombia (Remoto)',
        }),
        label='Ubicación'
    )
    
    salary_range = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'ej: $3.000.000 - $5.000.000 COP',
        }),
        label='Rango salarial (opcional)'
    )
    
    requirements = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'Escribe un requisito por línea:\n- 3 años de experiencia en Python\n- Conocimiento en Django\n- Inglés intermedio',
            'rows': 5
        }),
        label='Requisitos (opcional)'
    )
    
    benefits = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'Escribe un beneficio por línea:\n- Trabajo remoto\n- Seguro médico\n- Bonos por desempeño',
            'rows': 5
        }),
        label='Beneficios (opcional)'
    )


class EditPostForm(forms.Form):
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 15
        }),
        label='Contenido del post'
    )