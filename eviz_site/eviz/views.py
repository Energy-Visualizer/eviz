# Django imports
from django.shortcuts import render, redirect, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives # for email verification
from django.views.decorators.csrf import csrf_exempt

# Eviz imports
from eviz.utils import *
from eviz.forms import SignupForm, LoginForm

# Visualization imports
from plotly.offline import plot

@time_view
def index(request):
    '''Render the 'Index' page.'''
    return render(request, "index.html")

@time_view
def get_data(request):
    """ Handle data retrieval requests and return CSV data based on the query.

    Inputs:
        request (HttpRequest): The HTTP request object.

    Outputs:
        HttpResponse: A response containing CSV data or an error message.
    """
    if request.method == "POST":
        
        # set up query and get csv from it
        query = shape_post_request(request.POST)

        if not iea_valid(request.user, query):
            return HttpResponse("You do not have access to IEA data.") # TODO: make this work with status = 403, problem is HTMX won't show anything

        # Translate the query to match database field names
        query = translate_query(query)

        # Generate CSV data based on the query
        csv = get_csv_from_query(query)

        # set up the response:
        # content is the csv made above
        # then give csv MIME 
        # and appropriate http header
        final_response = HttpResponse(
            content = csv,
            content_type = "text/csv",
            headers = {"Content-Disposition": 'attachment; filename="eviz_data.csv"'} # TODO: make this file name more descriptive
        )

        # TODO: excel downloads
        # MIME for workbook is application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
        # file handle is xlsx for workbook 

    return final_response

@csrf_exempt
@time_view
def get_plot(request):
    """Generate and return a plot based on the POST request data.
    
    This function handles different types of plot types (sankey, xy_plots, matrices) and manages 
    user access to IEA data. It also updates the user's plot history.
    
    Inputs:
        request (HttpRequest): The HTTP request object.

    Outputs:
        HttpResponse: A response containing the plot HTML or an error message.
    """
    plot_div = None
    if request.method == "POST":
        # Extract plot type and query parameters from the POST request
        plot_type, query = shape_post_request(request.POST, get_plot_type = True)

        # Check if the user has access to IEA data
        # TODO: make this work with status = 403, problem is HTMX won't show anything
        if not iea_valid(request.user, query):
            return HttpResponse("You do not have access to IEA data. Please contact <a style='color: #00adb5' :visited='{color: #87CEEB}' href='mailto:matthew.heun@calvin.edu'>matthew.heun@calvin.edu</a> with questions."
                                "You can also purchase WEB data at <a style='color: #00adb5':visited='{color: #87CEEB}' href='https://www.iea.org/data-and-statistics/data-product/world-energy-balances'> World Energy Balances</a>.")
        
        # Use match-case to handle different plot types
        match plot_type:
            case "sankey":
                query = translate_query(query)
                sankey_diagram = get_sankey(query)

                if sankey_diagram == None:
                    plot_div = "No cooresponding data"

                else:
                    sankey_diagram.update_layout(title_text="Test Sankey", font_size=10)
                    plot_div = plot(sankey_diagram, output_type="div", include_plotlyjs=False)

            case "xy_plot":
                # Extract specific parameters for xy_plot
                efficiency_metric = query.pop('efficiency', None)
                color_by = query.pop("color_by", None)
                line_by = query.pop("line_by", None)
                facet_col_by = query.pop("facet-col-by", None)
                facet_row_by = query.pop("facet-row-by", None)
                energy_type = query.get("energy_type")
                
                # Handle combined Energy and Exergy case
                if 'Energy' in energy_type and 'Exergy' in energy_type:
                    energy_type = 'Energy, Exergy'
                
                query = translate_query(query)
                xy = get_xy(efficiency_metric, query, color_by, line_by, facet_col_by, facet_row_by, energy_type)
                plot_div = plot(xy, output_type="div", include_plotlyjs=False)

            case "matrices":
                # Extract specific parameters for matrices
                matrix_name = query.get("matname")
                color_scale = query.pop('color_scale', "viridis")
                # Retrieve the matrix
                query = translate_query(query)
                matrix = get_matrix(query)
                
                if matrix is None:
                    plot_div = "No corresponding data"
                
                else:
                    heatmap= visualize_matrix(matrix, color_scale)

                    heatmap.update_layout(
                        title = matrix_name + " Matrix",
                        yaxis = dict(title=''),
                        xaxis = dict(title=''),
                        xaxis_side = "top",
                        xaxis_tickangle = -45, 
                        scattermode = "overlay"
                        
                    )

                    # Render the figure as an HTML div
                    plot_div = plot(heatmap, output_type="div", include_plotlyjs="False")
        

            case _: # default
                plot_div = "Plot type not specified or supported"
                
        response = HttpResponse(plot_div)
        
        # Update user history
        plot_type, query = shape_post_request(request.POST, get_plot_type = True)
        serialized_data = update_user_history(request, plot_type, query)
        # Set cookie to expire in 30 days
        response.set_cookie('user_history', serialized_data.hex(), max_age=30 * 24 * 60 * 60)
            
    return response

import json
from django.urls import reverse
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import pickle  # Make sure this is imported

def render_history(request):
    """
    Render the user's plot history as HTML.
    
    This function retrieves the user's plot history from cookies
    and formats it as HTML buttons with delete functionality for each item.
    
    Args:
        request: The HTTP request object.
    
    Returns:
        HttpResponse: An HTTP response containing the HTML representation of the user's plot history.
    """
    # Retrieve the user's plot history from cookies
    user_history = get_user_history(request)
    history_html = ''
    
    if user_history:
        # Iterate through each history item and create HTML buttons
        for index, history_item in enumerate(user_history):
            # Create HTML for each history item, including plot and delete buttons
            history_html += f'''
            <div class="history-item">
                <button type="button" 
                    hx-vals='{json.dumps(history_item)}' 
                    hx-indicator="#plot-spinner" 
                    hx-post="/plot" 
                    hx-target="#plot-section" 
                    hx-swap="innerHTML" 
                    onclick='document.getElementById("plot-section").scrollIntoView();' 
                    class="history-button">
                    Plot Type: {history_item["plot_type"].capitalize()}<br>
                    Dataset: {history_item["dataset"]}<br>
                    Country: {history_item["country"]}
                </button>
                <button class="delete-history" 
                    hx-post="{reverse('delete_history_item')}" 
                    hx-vals='{{"index": {index}}}' 
                    hx-target="#history-list" 
                    hx-swap="innerHTML">
                    <i class="fas fa-trash-alt"></i>
                </button>
            </div><br>
            '''
    else:
        # If no history is available, display a message
        history_html = '<p>No history available.</p>'
    
    return HttpResponse(history_html)

@require_POST
@csrf_exempt
def delete_history_item(request):
    
    """
    Delete a specific item from the user's plot history.
    
    This function handles POST requests to delete a history item.
    It updates the user's history cookie after deletion.
    
    Inputs:
        request: The HTTP request object containing the index of the item to delete.
    
    Outputs:
        HttpResponse: A response containing the updated history HTML or an error message.
    """
    # Get the index of the item to delete from the POST data
    print("POST data:", request.POST)
    index = int(request.POST.get('index', -1))
    print("Index to delete:", index)
    
    if index >= 0:
        # Retrieve the current user history
        user_history = get_user_history(request)
        print("Current user history:", user_history)
        
        # Check if the index is valid
        if 0 <= index < len(user_history):
            # Remove the item at the specified index
            del user_history[index]
            
            # Serialize the updated history
            serialized_data = pickle.dumps(user_history)
            
            if user_history:
                # If there are still items in the history, render them
                response = render_history(request)
            else:
                # If the history is now empty, return a message
                response = HttpResponse('<p>No history available.</p>')
            
            # Update the user's history cookie
            response.set_cookie('user_history', serialized_data.hex(), max_age=30 * 24 * 60 * 60)
            
            return response
    
    # Return an error response if the request is invalid
    return HttpResponse("Invalid request", status=400)


@login_required(login_url="/login")
@time_view
def visualizer(request):
    """ Render the visualizer page with all necessary data for the user interface.
    
    This view requires user authentication and is timed for performance monitoring.
    
    Inputs:
        request: The HTTP request object

    Outputs:
        Rendered HTML response of the visualizer page with context data
    """
    # Fetch all available options for various parameters from the Translator
    datasets = Translator.get_all('dataset')
    countries = Translator.get_all('country')
    countries.sort()
    methods = Translator.get_all('method')
    energy_types = Translator.get_all('energytype')
    last_stages = Translator.get_all('laststage')
    ieamws = Translator.get_all('ieamw')
    grossnets = Translator.get_all('grossnet')
    # Remove 'Both' from ieamws if present
    try:
        ieamws.remove("Both")
    except ValueError:
        pass # don't care if it's not there, we're trying to remove it anyways
    matnames = Translator.get_all('matname')
    matnames.sort(key=len)  # sort matrix names by how long they are... seems reasonable
    
    # Prepare the context dictionary for the template
    context = {
        "datasets":datasets, "countries":countries, "methods":methods,
        "energy_types":energy_types, "last_stages":last_stages, "ieamws":ieamws, "grossnets":grossnets,
        "matnames":matnames, 
        "iea":request.user.is_authenticated and request.user.has_perm("eviz.get_iea")
        }

    return render(request, "visualizer.html", context)

def about(request):
    ''' Render the 'About' page.'''
    return render(request, 'about.html')

def terms_and_conditions(request):
    ''' Render the 'Terms and Conditions' page.'''
    return render(request, 'terms_and_conditions.html')

def data_info(request):
    ''' Render the 'Data Information' page.'''
    # Retrieve all Dataset objects from the database
    datasets = Dataset.objects.all()
    return render(request, 'data_info.html', context = {"datasets":datasets})

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
    if request.method == 'POST':
        # Create a form instance with the submitted data
        form = SignupForm(request.POST)
        if form.is_valid():
            # Extract the email from the cleaned form data
            new_user_email = form.cleaned_data["email"]

            # handle the email construction and sending
            code = new_email_code(form)
            msg = EmailMultiAlternatives(
                subject="New EVIZ Account",
                body=f"Please visit the following link to verify your account:\neviz.cs.calvin.edu/verify?code={str(code)}",
                from_email="eviz.site@outlook.com",
                to=[new_user_email]
            )
            # Email message
            msg.attach_alternative(
                content = f"<p>Please <a href='https://eviz.cs.calvin.edu/verify?code={str(code)}'>click here</a> to verify your new EVIZ account!</p>",
                mimetype = "text/html"
            )
            msg.send()

            # send the user to a page explaining what to do next (check email)
            return render(request, 'verify_explain.html')
    else:
        # If it's a GET request, create an empty form
        form = SignupForm()
    return render(request, 'signup.html', {'form': form})

from pickle import loads as pickle_loads
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
        new_user = EmailAuthCodes.objects.get(code = code) # try to get associated user from code
        if new_user:
            # if there is an associated user, set up their account
            # load the serialized account info from the database and save it
            account_info = pickle_loads(new_user.account_info)
            SignupForm(account_info).save()
            new_user.delete() # get rid of row in database
            messages.add_message(request, messages.INFO, "Verification was successful!")
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
    # for if a user is stopped and asked to log in first
    if request.method == 'GET':
        # get where they were trying to go
        requested_url = request.GET.get("next")
        if requested_url:
            request.session['requested_url'] = requested_url
        else:
            request.session['requested_url'] = None
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
    # Call Django's built-in logout function to log out the current user
    # This function removes the authenticated user's ID from the request and flushes their session data
    logout(request)
    return redirect('home')


# Static handling
from django.conf import settings
def handle_css_static(request, filepath):
    """Serve CSS static files directly from a specified directory.

    This function reads a CSS file from a static files directory
    and serves it as an HTTP response with the appropriate content type.

    Inputs:
        request: The HTTP request object (not used in this function, but typically included for view functions)
        filepath: The path to the CSS file relative to the static files directory

    Outputs:
        HttpResponse containing the contents of the CSS file
    """
    with open(f"{settings.STATICFILES_DIRS[1]}/{filepath}", "rb") as f:
        return HttpResponse(f.read(), headers = {"Content-Type": "text/css"})
    