from scipy.sparse import coo_matrix
from eviz.models import AggEtaPFU
from json import loads as json_from_string, dumps as json_dumps
from django.contrib.auth.models import User
import plotly.express as px  # for making the scatter plot
import pandas.io.sql as pd_sql  # for getting data into a pandas dataframe
from pandas import DataFrame
from eviz.models import *
import sys
from os import devnull
from django.db import connections
import plotly.graph_objects as pgo


from time import time
def time_view(v):
    '''Wrapper to time how long it takes to deliver a view

    Inputs:
        v, function: the view to time

    Outputs:
        A function which will also print how long the given view took to run to stdout
    '''

    def wrap(*args, **kwargs):
        t0 = time()
        ret = v(*args, **kwargs)
        t1 = time()
        print(f"Time to run {v.__name__}: {t1 - t0}")
        return ret

    return wrap


def translate_query(
    query: dict
) -> dict:
    '''Turn a query of human readable values from a form into a query read to hit the dataset

    Input:

        query, a dict: the query that should be translated

    Output:

        a dictionary of a query ready to hit the database
    '''

    translated_query = dict()  # set up to build and return at the end

    # common query parts

    if v := query.get("dataset"):
        translated_query["Dataset"] = Translator.dataset_translate(v)
    if v := query.get("country"):
        if type(v) == list:
            translated_query["Country__in"] = [
                Translator.country_translate(country) for country in v]
        else:
            translated_query["Country"] = Translator.country_translate(v)
    if v := query.get("method"):
        if type(v) == list:
            translated_query["Method__in"] = [
                Translator.method_translate(method) for method in v]
        else:
            translated_query["Method"] = Translator.method_translate(v)
    if v := query.get("energy_type"):
        if type(v) == list:
            translated_query["EnergyType__in"] = [
                Translator.energytype_translate(energy_type) for energy_type in v]
        else:
            translated_query["EnergyType"] = Translator.energytype_translate(v)
    if v := query.get("last_stage"):
        translated_query["LastStage"] = Translator.laststage_translate(v)
    if v := query.get("ieamw"):
        if type(v) == list:
            # both were selected, use the both option in the table
            translated_query["IEAMW"] = Translator.ieamw_translate("Both")
        else:
            translated_query["IEAMW"] = Translator.ieamw_translate(v)
    # includes neu either is in the query or not, it's value does need to be more than empty string, though
    translated_query["IncludesNEU"] = Translator.includesNEU_translate(
        bool(query.get("includes_neu")))
    if v := query.get("chopped_mat"):
        translated_query["ChoppedMat"] = Translator.matname_translate(v)
    if v := query.get("chopped_var"):
        translated_query["ChoppedVar"] = Translator.index_translate(v)
    if v := query.get("product_aggregation"):
        translated_query["ProductAggregation"] = Translator.agglevel_translate(
            v)
    if v := query.get("industry_aggregation"):
        translated_query["IndustryAggregation"] = Translator.agglevel_translate(
            v)

    # plot-specific query parts

    if v := query.get("to_year"):
        # if year part is a range of years, i.e. to_year present
        # set up query as range
        translated_query["Year__lte"] = int(v)
        if v := query.get("year"):
            translated_query["Year__gte"] = int(v)

    elif v := query.get("year"):
        # else just have year be one year
        translated_query["Year"] = int(v)

    if v := query.get("matname"):
        if v == "RUVY":
            translated_query["matname__in"] = [Translator.matname_translate("R"), Translator.matname_translate("U"), Translator.matname_translate("V"), Translator.matname_translate("Y")]
        else:
            translated_query["matname"] = Translator.matname_translate(v)

    return translated_query

def shape_post_request(
    payload, get_plot_type = False
) -> tuple[str, dict]:
    '''Turn a POST request payload into a ready to use query in a dictionary

    Input:

        payload, some dict-like (used with Django HttpRequest POST attributes): 
        the POST payload to shape into a query dictionary

        get_plot_type, bool: whether or not to get and give the plot type in the payload

    Output:

        a dictionary containing all the associations of a query parts and their values

        IF get_plot_type is True:

            2-tuple containing in top-down order

                a string telling the plot type requested

                a dictionary containing all the associations of a query parts and their values
    '''

    shaped_query = dict(payload)

    if get_plot_type:
        try:
            # to be returned at the end
            plot_type = shaped_query.pop("plot_type")[0]
        except KeyError:
            plot_type = None

    # get rid of security token, is not part of a query
    shaped_query.pop("csrfmiddlewaretoken", None)

    for k, v in shaped_query.items():

        # convert from list (if just one item in list)
        if len(v) == 1:
            shaped_query[k] = v[0]

    if get_plot_type:
        return (plot_type, shaped_query)
    return shaped_query


def iea_valid(user: User, query: dict) -> bool:
    '''Ensure that a give user's query does not give out IEA data if not authorized

    Inputs:

        user, user info from the HTTP request (for Django requsests: request.user): the user whose authorizations need to be checked

        query, a dict: the query to investigate

    Output:

        the boolean value of if a user's query is valid (True) or not (False)
    '''

    # will short curcuit if the data is free,
    # so everything past the "or" will not be checked if not neccessary
    return (
        # free data
        (
            query.get("dataset", None) != "IEAEWEB2022"
            and query.get("ieamw", None) == "MW"
        )
        or
        # authorized to get proprietary data
        (user.is_authenticated and user.has_perm("eviz.get_iea"))
    )

# TODO: is this all temp? do we want to keep all the data in seperate db's or will we actually use the dataset column?
def get_database(query: dict) -> str:
    db = Translator.dataset_translate(query["Dataset"])
    # TODO: this is missing IEA, we have to get where that is
    if db not in ["CLPFUv2.0a1", "CLPFUv2.0a2", "CLPFUv2.0a3"]:
        return None # database is invalid
    return db

from pathlib import Path
with open(f"{Path(__file__).resolve().parent.parent}/internal_resources/sankey_color_scheme.json") as f:
    colors_data = f.read()
SANKEY_COLORS: dict[str, str] = json_from_string(colors_data)
def get_sankey(query: dict) -> pgo.Figure:
    '''Gets a sankey diagram for a query

    Input:

        query, dict: a query ready to hit the database, i.e. translated as neccessary (see translate_query())

    Output:

        a plotly Figure with the sankey data

        or None if there is no cooresponding data for the query
    '''

    # we do a little shaping
    if "matname" in query.keys():
        del query["matname"]

    if (db := get_database(query)) is None:
        return None

    # get all four matrices to make the full RUVY matrix
    data = PSUT.objects.using(db).values_list("matname", "i", "j", "x").filter(
        **query, matname__in = [
            Translator.matname_translate("R"),
            Translator.matname_translate("U"),
            Translator.matname_translate("V"),
            Translator.matname_translate("Y")
        ]
    )

    # if no cooresponding data, return as such
    if not data:
        return None

    # get rid of any duplicate i,j,x combinations (many exist)
    data = set(data)

    # 5 lists, one for each column in the plot
    nodes = [list(), list(), list(), list(), list()]
    links = list()
    options = dict()

    # track which label is which index in the column lists
    label2index = dict()

    # i_idx and j_idx keep track of the index a new label is added to
    # this prevents having to repeatedly calculate the length of the
    # column lists
    # keys = column lists by index in nodes list above
    # values = index at which a new label will be added to a column list
    i_idx = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    j_idx = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}

    for matname, i, j, magnitude in data:
        row_name = Translator.index_translate(i)
        col_name = Translator.index_translate(j)

        from_node_col = to_node_col = -1

        # figure out which column the info should go in
        match(Translator.matname_translate(matname)):
            case("R"):
                from_node_col = 0
                to_node_col = 1

            case("U"):
                from_node_col = 1
                to_node_col = 2

            case("V"):
                from_node_col = 2
                to_node_col = 3

            case("Y"):
                from_node_col = 3
                to_node_col = 4

        # node_from / to_col will stay -1 if not processed above
        if from_node_col < 0 or to_node_col < 0:
            raise ValueError("Unknown matrix name processed")

        # get the from node
        from_node_idx = label2index.get(row_name, -1)
        if from_node_idx == -1:
            # add it if it is a new label and get new from_node_idx
            nodes[from_node_col].append(dict(label=row_name))
            label2index[row_name] = from_node_idx = i_idx[from_node_col]
            i_idx[from_node_col] += 1

        to_node_idx = label2index.get(col_name, -1)
        if to_node_idx == -1:
            nodes[to_node_col].append(dict(label=col_name))
            label2index[col_name] = to_node_idx = j_idx[to_node_col]
            j_idx[to_node_col] += 1

        # set up the flow from the two labels above
        links.append({"from": dict(column=from_node_col, node = from_node_idx),
                "to": dict(column=to_node_col, node = to_node_idx),
                "value": magnitude})

    # convert everything to json to send it to the javascript renderer
    return json_dumps(nodes), json_dumps(links), json_dumps(options)

def get_xy(efficiency_metric, query: dict) -> pgo.Figure:
    '''Gets an xy plot for a query

    Inputs:

        efficiency_metric, string: the efficiency matrix to get the plot for

        query, dict: a query ready to hit the database, i.e. translated as neccessary (see translate_query())

    Output:

        a plotly Figure with the xy data
    '''

    # get the respective data from the database
    df = get_dataframe(AggEtaPFU, query, ["Year", efficiency_metric])
        
    if df.empty: return None # if no data, return as such

    return px.line(
        df, x="Year", y=efficiency_metric,
        title=f"Efficiency of {efficiency_metric} by year",
        template="plotly_dark"
    )


def get_matrix(query: dict) -> coo_matrix:
    '''Collects, constructs, and returns one of the RUVY matrices

    Inputs:
        a query ready to hit the database, i.e. translated as neccessary (see translate_query())

    Outputs:
        A scipy coo_matrix containing all the values from the specified query
        or None if the given query related to no data 
    '''

    if (db := get_database(query)) is None:
        return None

    # Get the sparse matrix representation
    # i, j, x for row, column, value
    # in 3-tuples
    sparse_matrix = (
        PSUT.objects
        .using(db)
        .values_list("i", "j", "x")
        .filter(**query)
    )

    # if nothing was returned
    if not sparse_matrix:
        return None

    # Get dimensions for a matrix (rows and columns will be the same)
    # len() would evaluate the query set, so use count() instead for better performance
    matrix_nrow = Index.objects.all().count()

    # For each 3-tuple in sparse_matrix
    # Put together all the first values, all the second, etc.
    # All first values across the tupes are rows, second are columns, etc.
    row, col, val = zip(*sparse_matrix)

    # Make and return the sparse matrix
    return coo_matrix(
        (val, (row, col)),
        shape=(matrix_nrow, matrix_nrow),
    )


def visualize_matrix(mat: coo_matrix) -> pgo.Figure:
    # Convert the matrix to a format suitable for Plotly's heatmap
    rows, cols, vals = mat.row, mat.col, mat.data
    row_labels = [Translator.index_translate(i) for i in rows]
    col_labels = [Translator.index_translate(i) for i in cols]
    heatmap = pgo.Heatmap(
        z=vals,
        x=col_labels,
        y=row_labels,
        text=vals,
        texttemplate="%{text:.2f}",
        showscale=False,
    )

    # convert to a more general figure
    return pgo.Figure(data=heatmap)

def get_dataframe(model: models.Model, query: dict, columns: list) -> DataFrame:
    if (db := get_database(query)) is None:
        return DataFrame() # empty data frame if database is wrong
    
    # get the data from database
    db_query = model.objects.filter(**query).values(*columns).query
    with Silent():
        df = pd_sql.read_sql_query(
            str(db_query),
            con=connections[db].cursor().connection # get the connection associated with the requested database
        )
    
    return df

COLUMNS = ["Dataset", "Country", "Method", "EnergyType", "LastStage", "IEAMW", "IncludesNEU", "Year", "ChoppedMat", "ChoppedVar", "ProductAggregation", "IndustryAggregation", "matname", "i", "j", "x"]
def get_psut_translated_dataframe(query: dict, columns: list) -> DataFrame:
    df = get_dataframe(PSUT, query, columns)

    # no need to do work if dataframe is empty (no data was found for the query)
    if df.empty: return df

    translate_columns = {
        'Dataset': Translator.dataset_translate,
        'Country': Translator.country_translate,
        'Method': Translator.method_translate,
        'EnergyType': Translator.energytype_translate,
        'LastStage': Translator.laststage_translate,
        'IEAMW': Translator.ieamw_translate,
        'ChoppedMat': Translator.matname_translate,
        'ChoppedVar': Translator.index_translate,
        'ProductAggregation': Translator.agglevel_translate,
        'IndustryAggregation': Translator.agglevel_translate,
        'matname': Translator.matname_translate,
        'i': Translator.index_translate,
        'j': Translator.index_translate
    }

    for col, translate_func in translate_columns.items():
        if col in df.columns:
            df[col] = df[col].apply(translate_func)
    
    # Handle IncludesNEU separately as it's a boolean
    if 'IncludesNEU' in df.columns:
        df['IncludesNEU'] = df['IncludesNEU'].apply(lambda x: 'Yes' if x else 'No')
    
    return df

def get_csv_from_query(query: dict, columns: list = COLUMNS):
    
    # index false to not have column of row numbers
    return get_psut_translated_dataframe(query, columns).to_csv(index=False)

def get_excel_from_query(query: dict, columns = COLUMNS):

    # index false to not have column of row numbers
    return get_psut_translated_dataframe(query, columns).to_excel(index=False)

from bidict import bidict
from django.apps import apps
class Translator:
    # A dictionary where keys are model names and values are bidict objects
    __translations = {}

    @staticmethod
    def __load_bidict(model_name, id_field, name_field) -> bidict:
        """
        Load translations for a specific model if not already loaded.
        
        Args:
            model_name (str): The name of the model to load translations for.
            id_field (str): The name of the ID field in the model.
            name_field (str): The name of the field containing the human-readable name.
        
        Returns:
            bidict: A bidirectional dictionary of translations for the model.
        """
        if model_name not in Translator.__translations:
            # Get the model class dynamically
            model = apps.get_model(app_label='eviz', model_name=model_name)
            # Create a bidict with name:id pairs
            Translator.__translations[model_name] = bidict({getattr(item, name_field): getattr(item, id_field) for item in model.objects.all()})
        return Translator.__translations[model_name]

    @staticmethod
    def _translate(model_name, value, id_field, name_field):
        # Translate a value between its ID and name for a specific model.
        # value: The value to translate (can be either an ID or a name).
        # Returns: The translated value (either ID or name, depending on input).
        translations = Translator.__load_bidict(model_name, id_field, name_field)
        return translations.get(value) or translations.inverse.get(value, value)

    @staticmethod
    def index_translate(value):
        return Translator._translate('Index', value, 'IndexID', 'Index')

    @staticmethod
    def dataset_translate(value):
        return Translator._translate('Dataset', value, 'DatasetID', 'Dataset')

    @staticmethod
    def country_translate(value):
        return Translator._translate('Country', value, 'CountryID', 'FullName')

    @staticmethod
    def method_translate(value):
        return Translator._translate('Method', value, 'MethodID', 'Method')

    @staticmethod
    def energytype_translate(value):
        return Translator._translate('EnergyType', value, 'EnergyTypeID', 'FullName')

    @staticmethod
    def laststage_translate(value):
        return Translator._translate('LastStage', value, 'ECCStageID', 'ECCStage')

    @staticmethod
    def ieamw_translate(value):
        return Translator._translate('IEAMW', value, 'IEAMWID', 'IEAMW')

    @staticmethod
    def matname_translate(value):
        return Translator._translate('matname', value, 'matnameID', 'matname')

    @staticmethod
    def agglevel_translate(value):
        return Translator._translate('AggLevel', value, 'AggLevelID', 'AggLevel')

    @staticmethod
    def includesNEU_translate(value):
        return int(value) if isinstance(value, bool) else int(bool(value))

    @staticmethod
    def get_all(attribute):
        """
        Get all possible values for a given attribute.
        
        Args:
            attribute (str): The name of the attribute to get values for.
        
        Returns:
            list: A list of all possible values (names) for the attribute.
        """
        # Dictionary mapping attribute names to model details
        model_mappings = {
            'dataset': ('Dataset', 'DatasetID', 'Dataset'),
            'country': ('Country', 'CountryID', 'FullName'),
            'method': ('Method', 'MethodID', 'Method'),
            'energytype': ('EnergyType', 'EnergyTypeID', 'FullName'),
            'laststage': ('LastStage', 'ECCStageID', 'ECCStage'),
            'ieamw': ('IEAMW', 'IEAMWID', 'IEAMW'),
            'matname': ('matname', 'matnameID', 'matname'),
            'agglevel': ('AggLevel', 'AggLevelID', 'AggLevel'),
        }
        
        if attribute not in model_mappings:
            raise ValueError(f"Unknown attribute: {attribute}")
        
        # Get model details and load translations
        model_name, id_field, name_field = model_mappings[attribute]
        translations = Translator.__load_bidict(model_name, id_field, name_field)
        return list(translations.keys())

    @staticmethod
    def get_all_available(attribute):
        # Dictionary mapping attribute names to model details
        model_mappings = {
            'dataset': ('Dataset', 'DatasetID', 'Dataset'),
            'country': ('Country', 'CountryID', 'FullName'),
            'method': ('Method', 'MethodID', 'Method'),
            'energytype': ('EnergyType', 'EnergyTypeID', 'FullName'),
            'laststage': ('LastStage', 'ECCStageID', 'ECCStage'),
            'ieamw': ('IEAMW', 'IEAMWID', 'IEAMW'),
            'matname': ('matname', 'matnameID', 'matname'),
            'agglevel': ('AggLevel', 'AggLevelID', 'AggLevel'),
        }
        
        if attribute not in model_mappings:
            raise ValueError(f"Unknown attribute: {attribute}")
        
        model_name, id_field, name_field = model_mappings[attribute]
        translations = Translator.__load_bidict(model_name, id_field, name_field)

        print(PSUT.objects.order_by().values_list(model_name, flat=True).distinct())

    @staticmethod
    def get_includesNEUs():
        return [True, False]

# TODO: this needs to be fixed...
# def temp_add_get():

#     def mat_get(self, row, col):
#             if type(row) != str or type(col) != str:
#                 raise ValueError("Getting item from RUVY matrix must be as follows: matrix['row_name', 'column_name'] or matrix[row_number, col_number]")

#             if type(self) == csc_matrix:
#                 return self[Translator.index_translate(col), Translator.index_translate(row)]
#             return self[Translator.index_translate(row), Translator.index_translate(col)]

#     if not hasattr(csr_matrix, "get"): csr_matrix.get = mat_get

#     if not hasattr(csc_matrix, "get"): csc_matrix.get = mat_get


# Silent context manager


class Silent():
    '''Used as a context manager to silence anything in its block'''

    real_stdout = sys.stdout
    real_stderr = sys.stderr
    instance = None

    def __new__(cls):
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def __enter__(self):
        self.dn = open(devnull, "w")
        sys.stdout = self.dn
        sys.stderr = self.dn

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.dn.close()
        sys.stdout = self.real_stdout
        sys.stderr = self.real_stderr

from uuid import uuid4
import pickle
def new_email_code(form) -> str:
    code = str(uuid4())
    account_info = pickle.dumps(form.clean()) # get the cleaned form (a map) serialized
    EmailAuthCodes(code=code, account_info=account_info).save() # save account setup info to database
    return code

def get_user_history(request) -> list:
    serialized_data = request.COOKIES.get('user_history')

    if serialized_data:
        user_history = pickle.loads(bytes.fromhex(serialized_data))
    else:
        user_history = list()

    return user_history

MAX_HISTORY = 5
def update_user_history(request, plot_type, query):

    user_history = get_user_history(request)

    history_data = {
        'plot_type': plot_type,
        **query
    }

    # Check if user_history is not empty
    if user_history:

        # if query is already in history, remove it to move it to the top
        try:
            user_history.remove(history_data)
        except ValueError: pass # don't care if not in, trying to remove anyways

        user_history.insert(0, history_data) # finally, add the new query to the top of the history

        # if the queue is full, take the end off
        if len(user_history) > MAX_HISTORY: user_history.pop()

    else:
        # If user_history is empty, append the new history_data
        user_history.append(history_data)

    serialized_data = pickle.dumps(user_history)
    return serialized_data
