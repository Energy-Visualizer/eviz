from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import EvizUser
from django.contrib.auth.password_validation import validate_password

# at least one number, one lowercase, one uppercase, and at least 8 chars long
PASSWORD_PATTERN = r"(?=.*\d)(?=.*[a-z])(?=.*[A-Z]).{8,}"
# no period at end of title because browsers add the period automatically ??
PASSWORD_TITLE = "At least one number, one lowercase character, and one uppercase character. At least 8 characters long"

class SignupForm(UserCreationForm):
    """ Custom form for user registration
    
    This form extends Django's UserCreationForm to include addidtional fields
    specific for the Mexer application such as email, institution, and country.
    """
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Username', "pattern": r"[\w\d@\.\+-_]+", "title": "Only consist of letters, numbers, and '@', '.', '+', '-', or '_'"})
    )
    email = forms.CharField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'joe@gmail.com'})
    )
    institution_type = forms.ChoiceField(
        required=True,
        choices={
            "Academic": "Academic",
            "Government": "Government",
            "Industry": "Industry",
            "Non-Profit": "Non-Profit",
            "Other": "Other"
        }
    )
    institution_name = forms.CharField(
        required=False,
        label="Institution Name (Optional)", # specifed expicitly to add optional tag
        widget=forms.TextInput(attrs={'placeholder': "e.g. Calvin University"})
    )
    country = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'placeholder': "e.g. United States"})
    )
    password1 = forms.CharField(
        label="Password",
        required=True,
        widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'pattern': PASSWORD_PATTERN, 'title': PASSWORD_TITLE})
    )
    password2 = forms.CharField(
        label="Confirm Password",
        required=True,
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password', 'pattern': PASSWORD_PATTERN, 'title': PASSWORD_TITLE})
    )

    class Meta:
        # Use the custom custom user model
        model = EvizUser 
        fields = ['username', 'email', 'password1', 'password2', 'institution_type', 'institution_name', 'country']

class ResetForm(forms.ModelForm):

    password1 = forms.CharField(
        label="Password",
        required=True,
        widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'pattern': PASSWORD_PATTERN, 'title': PASSWORD_TITLE})
    )
    password2 = forms.CharField(
        label="Confirm Password",
        required=True,
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password', 'pattern': PASSWORD_PATTERN, 'title': PASSWORD_TITLE})
    )

    def valid_pass_provided(self) -> bool:
        try:
            validate_password(self.cleaned_data["password1"], EvizUser)
        except Exception as e:
            self.add_error(field=None, error=e)
            return False

        if self.cleaned_data["password1"] != self.cleaned_data["password2"]:
            self.add_error(field=None, error="Passwords must match.")
            return False

        return True
    
    # overrides default is_valid to add password same password checking
    def is_valid(self) -> bool:
        return (
            super().is_valid()
            and self.valid_pass_provided()
        )

    class Meta:
        model = EvizUser
        fields = ['password1', 'password2']

class LoginForm(forms.Form):
    """Custom form foruser login.
    
    This form provides fields for username and password input for user authentication.
    """
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Username'})
    )
    password = forms.CharField(
        label="Password",
        required=True,
        widget=forms.PasswordInput(attrs={'placeholder': 'Password'})
    )