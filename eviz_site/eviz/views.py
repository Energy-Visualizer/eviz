# Django imports
from django.shortcuts import render, redirect, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

# Eviz imports
from eviz.utils import *
from eviz.forms import SignupForm, LoginForm

# Visualization imports
from plotly.offline import plot

@time_view
def index(request):
    return render(request, "index.html")

# TODO: this is temp
from random import choice
@time_view
def get_psut_data(request):
    
    query0 = dict(
        dataset = "CLPFUv2.0a2",
        country = "KEN",
        method = "PCM",
        energy_type = "E",
        last_stage = "Final",
        ieamw = "Both",
        includes_neu = False,
        year = 1985,
        chopped_mat = "None",
        chopped_var = "None",
        product_aggregation = "Specified",
        industry_aggregation = "Specified"
    )

    query1 = dict(
        dataset = "CLPFUv2.0a2",
        country = "FRA",
        method = "PCM",
        energy_type = "E",
        last_stage = "Useful",
        ieamw = "Both",
        includes_neu = False,
        year = 1985,
        chopped_mat = "None",
        chopped_var = "None",
        product_aggregation = "Despecified",
        industry_aggregation = "Despecified"
    )

    query2 = dict(
        dataset = "CLPFUv2.0a2",
        country = "LTU",
        method = "PCM",
        energy_type = "E",
        last_stage = "Useful",
        ieamw = "IEA",
        includes_neu = False,
        year = 2019,
        chopped_mat = "None",
        chopped_var = "None",
        product_aggregation = "Despecified",
        industry_aggregation = "Despecified"
    )

    query3 = dict(
        dataset = "CLPFUv2.0a2",
        country = "JAM",
        method = "PCM",
        energy_type = "X",
        last_stage = "Final",
        ieamw = "Both",
        includes_neu = False,
        year = 2002,
        chopped_mat = "None",
        chopped_var = "None",
        product_aggregation = "Grouped",
        industry_aggregation = "Despecified"
    )

    query4 = dict(
        dataset = "CLPFUv2.0a2",
        country = "UnDEU",
        method = "PCM",
        energy_type = "X",
        last_stage = "Useful",
        ieamw = "IEA",
        includes_neu = True,
        year = 1961,
        chopped_mat = "None",
        chopped_var = "None",
        product_aggregation = "Despecified",
        industry_aggregation = "Despecified"
    )

    query = choice([query0, query1, query2, query3, query4])

    rows_r = get_matrix(**query, matrix_name="R")

    rows_u = get_matrix(**query, matrix_name="U")
    
    rows_v = get_matrix(**query, matrix_name="V")
    
    rows_y = get_matrix(**query, matrix_name="Y")
    
    context = {
        "query": query,
        "r_mat": rows_r,
        "u_mat": rows_u,
        "v_mat": rows_v,
        "y_mat": rows_y,
    }

    return render(request, "./test.html", context)

import plotly.graph_objects as go
@time_view
def get_plot(request):

    plot_div = None
    if request.method == "POST":

        plot_type, query = shape_post_request(request.POST)

        if not iea_valid(request.user, query):
            return HttpResponse("You are not allowed to receive IEA data.")
        
        match plot_type:
            case "sankey":
                query = translate_query(query)
                sankey_diagram = get_sankey(query)
                if sankey_diagram == None:
                    plot_div = "No cooresponding data"
                else:
                    sankey_diagram.update_layout(title_text="Test Sankey", font_size=10)
                    plot_div = plot(sankey_diagram, output_type="div", include_plotlyjs=False)

                    # add the reset button and start up the plot panning and zomming
                    plot_div += '<button id="plot-reset" onclick="initPlotUtils()">RESET</button>' + '<script>initPlotUtils()</script>'

            case "xy_plot":
                efficiency_metric = query.pop('efficiency')
                query = translate_query(query)
                xy = get_xy(efficiency_metric, query)
                plot_div = plot(xy, output_type="div", include_plotlyjs=False)

            case "matrices":
                # Retrieve the matrix using the get_matrix function
                matrix = get_matrix(query)

                if matrix is None:
                    plot_div = "No corresponding data"
                
                else:
                    # Convert the matrix to a format suitable for Plotly's heatmap
                    matrix = matrix.tocoo()
                    rows, cols, vals = matrix.row, matrix.col, matrix.data
                    row_labels = [Translator.index_reverse_translate(i) for i in rows]
                    col_labels = [Translator.index_reverse_translate(i) for i in cols]
                    heatmap = go.Heatmap(
                        z=vals,
                        x=col_labels,
                        y=row_labels,
                        text=vals,
                        texttemplate="%{text:.2f}",
                        showscale=False,
                    )
                    matname = query.get('matname')
                    # Create a layout for the heatmap
                    layout = go.Layout(
                        title= f"Matrix Visualization: {matname}",
                        xaxis=dict(title=''),
                        yaxis=dict(title=''),
                    )

                    # Create a figure with the heatmap data and layout
                    fig = go.Figure(data=heatmap, layout=layout)

                    # Render the figure as an HTML div
                    plot_div = plot(fig, output_type="div", include_plotlyjs="False")

            case _: # default
                plot_div = "Plot type not specified or supported"
    
    return HttpResponse(plot_div)

@login_required(login_url="/login")
@time_view
def visualizer(request):
    datasets = Translator.get_datasets()
    countries = list(Translator.get_countries())
    countries.sort()
    methods = Translator.get_methods()
    energy_types = Translator.get_energytypes()
    last_stages = Translator.get_laststages()
    ieamws = Translator.get_ieamws()
    includes_neus = Translator.get_includesNEUs()
    years = range(1800,2021)
    matnames = list(Translator.get_matnames())
    matnames.sort(key=len) # sort matrix names by how long they are... seems reasonable
    
    context = {"datasets":datasets, "countries":countries, "methods":methods,
            "energy_types":energy_types, "last_stages":last_stages, "ieamws":ieamws,
            "includes_neus":includes_neus, "years":years, "matnames":matnames
            }

    return render(request, "visualizer.html", context)

def about(request):
    return render(request, 'about.html')

def user_signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = SignupForm()
    return render(request, 'signup.html', {'form': form})

def user_login(request):
    # for if a user is stopped and asked to log in first
    if request.method == 'GET':
        # get where they were trying to go
        requested_url = request.GET.get("next", None)
        if requested_url:
            request.session['requested_url'] = requested_url
        else:
            request.session['requested_url'] = None
        form = LoginForm()

    # for if the user submitted their login form
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)

            # if user was successfully authenticated
            if user:
                login(request, user)
                requested_url = request.session.get('requested_url')
                if requested_url: # if user was trying to go somewhere else originally
                    request.session['requested_url'] = None
                    return redirect(requested_url)
                # else just send them to the home page
                return redirect('home')
            # TODO: else show failure to log in page
    else:
        form = LoginForm()
    
    # giving the normal login page
    return render(request, 'login.html', {'form': form})

def user_logout(request):
    logout(request)
    return redirect('login')



# Static handling
from django.conf import settings
def handle_css_static(request, filepath):
    with open(f"{settings.STATICFILES_DIRS[1]}/{filepath}", "rb") as f:
        return HttpResponse(f.read(), headers = {"Content-Type": "text/css"})