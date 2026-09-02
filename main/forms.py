import os

from django import forms
from .models import Newsletter, Comment, JobApplication


class NewsletterForm(forms.ModelForm):
    class Meta:
        model = Newsletter
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'newsletter-input',
                'placeholder': 'Your email address',
                'required': True,
            })
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower().strip()
        return email


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['name', 'email', 'website', 'content']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your Name *',
                'required': True,
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your Email *',
                'required': True,
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your Website (optional)',
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Your Comment *',
                'rows': 5,
                'required': True,
            })
        }
    
    def clean_content(self):
        content = self.cleaned_data.get('content')
        if content and len(content.strip()) < 10:
            raise forms.ValidationError('Comment must be at least 10 characters long.')
        return content


class JobApplicationForm(forms.ModelForm):
    class Meta:
        model = JobApplication
        fields = ['name', 'email', 'phone', 'cv', 'cover_message']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full Name *',
                'required': True,
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email Address *',
                'required': True,
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone Number *',
                'required': True,
            }),
            'cv': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx',
            }),
            'cover_message': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Tell us why you are a great fit (optional)',
                'rows': 4,
            }),
        }

    ALLOWED_CV_EXTENSIONS = ['.pdf', '.doc', '.docx']
    MAX_CV_SIZE = 5 * 1024 * 1024  # 5 MB

    def clean_cv(self):
        cv = self.cleaned_data.get('cv')
        if cv:
            ext = os.path.splitext(cv.name)[1].lower()
            if ext not in self.ALLOWED_CV_EXTENSIONS:
                raise forms.ValidationError('CV must be a PDF, DOC, or DOCX file.')
            if cv.size > self.MAX_CV_SIZE:
                raise forms.ValidationError('CV file size must be under 5 MB.')
        return cv


class BlogSearchForm(forms.Form):
    q = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'search-input',
            'placeholder': 'Search real estate insights...',
            'required': False,
        })
    )