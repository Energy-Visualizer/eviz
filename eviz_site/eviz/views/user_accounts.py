####################################################################
# user_accounts.py includes all views related to user accounts
# 
# Signup, signin, and signout are included
# Along with pages for user's to manage their account
# such as password resets
#
# The email verification of the signup process is also here
# 
# Authors:
#       Kenny Howes - kmh67@calvin.edu
#       Edom Maru - eam43@calvin.edu 
#####################
from utils.logging import LOGGER
from eviz.forms import SignupForm, LoginForm
from eviz.views.error_pages import *
from utils.misc import new_email_code, new_reset_code, valid_passwords
from django.core.mail import EmailMultiAlternatives # for email verification
from eviz.models import EmailAuthCode, PassResetCode, EvizUser
import pickle
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout


def user_signup(request):
    """ Handle user signup process.

    This function manages both GET and POST requests for user signup.
    For POST requests, it processes the form, sends a verification email,
    and redirects to an explanation page.
    For GET requests, it displays the signup form.

    Inputs:
        request: The HTTP request object

    Outputs:
        Rendered HTML response, either the signup form or a verification explanation page
    """
    LOGGER.info("Signup page visted.")

    if request.method == 'POST':
        # Create a form instance with the submitted data
        form = SignupForm(request.POST)
        if form.is_valid():
            
            # Extract the email from the cleaned form data
            new_user_email = form.cleaned_data.get("email")
            if new_user_email == None:
                return error_400(request, "No email in signup")

            LOGGER.info(f"{form.cleaned_data['username']} signed up for account w/ email {new_user_email}.")

            # handle the email construction and sending
            code = new_email_code(account_info = form.clean())
            url = f"https://mexer.site/verify?code={code}"
            msg = EmailMultiAlternatives(
                subject="New Mexer Account",
                body=f"Please visit the following link to verify your account:\n{url}",
                from_email="signup@mexer.site",
                to=[new_user_email]
            )
            # HTML message
            msg.attach_alternative(
                content = f"<p>Please <a href='{url}'>click here</a> to verify your new Mexer account!</p>",
                mimetype = "text/html"
            )
            
            # send the email and make sure it was successful
            # 0 is failure
            if msg.send() == 0:
                LOGGER.error(f"Couldn't send signup email to {new_user_email}")      
            else:
                LOGGER.info(f"Signup email sent to {new_user_email}.")

            # send the user to a page explaining what to do next (check email)
            return render(request, 'verify_explain.html')
    else:
        # If it's a GET request, create an empty form
        form = SignupForm()
    return render(request, 'signup.html', {'form': form})

def verify_email(request):
    """ Verify a user's email address using a verification code.

    This function handles the email verification process when a user clicks
    the verification link sent to their email during signup.

    Inputs:
        request: The HTTP request object, expected to contain a 'code' parameter in GET

    Outputs:
        Redirects to the login page with a success or failure message
    """
    if request.method == "GET":
        # Extract the verification code from the GET parameters
        code = request.GET.get("code")

        new_user = None
        try: 
            new_user = EmailAuthCode.objects.get(code = code) # try to get associated user from code
        except Exception as e: 
            return error_400(request, e) # bad request, no new user found

        if new_user:
            # if there is an associated user, set up their account
            # load the serialized account info from the database and save it
            account_info = pickle.loads(new_user.account_info)
            SignupForm(account_info).save()
            new_user.delete() # get rid of row in database
            messages.add_message(request, messages.INFO, "Verification was successful!")
            LOGGER.info(f"{account_info.get('username')} account created.")
        else:
            messages.add_message(request, messages.INFO, "Bad verification code!")

    return redirect("login")

def user_login(request):
    """ Handle user login process.

    This function manages both GET and POST requests for user login.
    It handles cases where users are redirected to login from another page,
    as well as direct login attempts.

    Inputs:
        request: The HTTP request object

    Outputs:
        Rendered login page or redirect to appropriate page after successful login
    """
    LOGGER.info("Logon page visted.")
    
    # for if a user is stopped and asked to log in first
    if request.method == 'GET':
        # get where they were trying to go
        requested_url = request.GET.get("next")
        if requested_url:
            request.session['requested_url'] = requested_url
        form = LoginForm()

    # for if the user submitted their login form
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            # Extract username and password from the cleaned form data
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)

            # if user was successfully authenticated
            if user:
                login(request, user) # log the user in so they don't have to repeat authentication every time
                LOGGER.info(f"{user.username} logged on.")
                requested_url = request.session.get('requested_url')
                if requested_url: # if user was trying to go somewhere else originally
                    del request.session['requested_url']
                    return redirect(requested_url)
                # else just send them to the home page
                return redirect('home')
            else:
                messages.add_message(request, messages.ERROR, "Username or password is incorrect!")
    else:
        form = LoginForm()
    
    # giving the normal login page
    return render(request, 'login.html', {'form': form})

def user_logout(request):
    """ Handle user logout process. """
    LOGGER.info(f"{request.user.get_username()} logged off.")
    # Call Django's built-in logout function to log out the current user
    # This function removes the authenticated user's ID from the request and flushes their session data
    logout(request)
    return redirect('home')

def forgot_password(request):

    if request.method == "GET":
        # start the reset process
        return render(request, "reset.html") # page with form to get which user is requesting the reset

    elif request.method == "POST":
        # a user has submitted their username for a password reset
        # get the username given and try to send an email to the
        # account cooresponding inbox
        username: str = request.POST.get("username")

        try:
            user = EvizUser.objects.get_by_natural_key(username)
        except Exception as e:
            # bad request, no user found
            # simply ignore the rest of the process
            LOGGER.error(f"Reset requested for username {username}: {e}")
        else:
            # if a user was found for the given username
            # construct and send the email
            LOGGER.info(f"Sending password reset email for {username}")
            code = new_reset_code(user)
            url = f"https://mexer.site/reset-password?code={code}"
            msg = EmailMultiAlternatives(
                subject="Mexer Password Reset",
                body=f"Please visit the following link to reset your account:\n{url}",
                from_email="reset@mexer.site",
                to=[user.email]
            )

            # HTML message
            msg.attach_alternative(
                content = f"<p>Please <a href='{url}'>click here</a> to reset your Mexer password.</p>",
                mimetype = "text/html"
            )
            msg.send()
            LOGGER.info(f"Successfully sent password reset email for {username}")
        
        # NOTE: this is not in a final block because
        # django will not send any exceptions in the else
        # section to the terminal if there is a final block

        # send success and failure here
        # because we don't want to give away
        # whether accounts exist or not
        return render(request, "reset_explain.html")
        
def reset_password(request):
    
    if request.method == "GET":
        code = request.GET.get("code")
        return render(request, "reset-submit.html", context = {"code": code})
    
    elif request.method == "POST":
        ps1 = request.POST.get("password1")
        ps2 = request.POST.get("password2")
        code = request.POST.get("code")

        if not valid_passwords(ps1, ps2):
            # TODO: have more descriptive messages about why password(s) not valid
            messages.add_message(request, messages.ERROR, "Passwords not valid!")
            return render(request, "reset-submit.html", context = {"code": code})
        
        # try to get the user with the information provided
        try:
            pass_reset_row = PassResetCode.objects.get(code = code)
            user = pass_reset_row.user
        except Exception as e:
            # bad request, no user found
            return error_400(request, e)
        
        user.set_password(ps1)
        user.save()

        # if no errors getting the user,
        # delete the cooresponding row
        pass_reset_row.delete()

        return redirect("login")