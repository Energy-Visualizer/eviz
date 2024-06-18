from scipy.sparse import coo_matrix
from eviz.models import AggEtaPFU
from json import loads as json_from_string
from django.contrib.auth.models import User
import plotly.express as px  # for making the scatter plot
import pandas.io.sql as pd_sql  # for getting data into a pandas dataframe
from eviz.models import PSUT, Index, Dataset, Country, Method, EnergyType, LastStage, IEAMW, matname, AggLevel
import sys # for silencing stdout warnings (pandas using psycopg2 connection right now)
from os import devnull
from django.db import connection # for low-level psycopg2 connection. to access other db connections, import connections
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
    del shaped_query["csrfmiddlewaretoken"]

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


with open("internal_resources/sankey_color_scheme.json") as f:
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

    # get all four matrices to make the full RUVY matrix
    data = PSUT.objects.values_list("i", "j", "x").filter(**query, matname__in=[Translator.matname_translate(
        "R"), Translator.matname_translate("U"), Translator.matname_translate("V"), Translator.matname_translate("Y")])

    # if no cooresponding data, return as such
    if not data:
        return None

    # get rid of any duplicate i,j,x combinations (many exist)
    data = set(data)

    # begin constructing the sankey
    # used to know which human-readable label is where in the label list
    label_to_index = dict()
    next_index = 0  # used to keep track of where a new label is added in the label list

    labels = list()  # used to keep track of all the labels
    sources = list()  # used to keep track of all the sources (from-nodes)
    targets = list()  # used to keep track of all the targets (to-nodes)
    magnitudes = list()  # used to keep track of all the magnitudes between the nodes

    node_colors = list()
    flow_colors = list()

    for row, col, magnitude in data:
        translated_row = Translator.index_reverse_translate(row)
        translated_col = Translator.index_reverse_translate(col)

        flow_color = "rgba(100,100,100,0.5)"  # default flow color

        # Get the row (source) label's index and make the start of a connection
        idx = label_to_index.get(translated_row, -1)
        if idx == -1:  # label is new
            labels.append(translated_row)
            label_to_index[translated_row] = idx = next_index
            next_index += 1

            # get the associated color for the source, if there is one and apply it
            # if not, the color is wheat
            node_colors.append(SANKEY_COLORS.get(translated_row, "wheat"))

        sources.append(idx)

        # Get the col (target) label's index and make the end of a connection
        idx = label_to_index.get(translated_col, -1)
        if idx == -1:  # label is new
            labels.append(translated_col)
            label_to_index[translated_col] = idx = next_index
            next_index += 1

            # same as above
            node_colors.append(SANKEY_COLORS.get(translated_col, "wheat"))

        targets.append(idx)

        # Finish the connection with the magnitude of the connection
        magnitudes.append(magnitude)

        # make in-flow special color if node has special color
        #     i.e. if current target node has color besides default node color
        # only on targets (columns) because only targets can have in-flows
        if ((assoc_color := node_colors[idx]) != "wheat"):
            flow_color = assoc_color

        flow_colors.append(flow_color)

    return pgo.Figure(data=[pgo.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            label=labels,
            color=node_colors
        ),
        link=dict(
            source=sources,
            target=targets,
            value=magnitudes,
            color=flow_colors
        ))])


def get_xy(efficiency_metric, query: dict) -> pgo.Figure:
    '''Gets an xy plot for a query

    Inputs:

        efficiency_metric, string: the efficiency matrix to get the plot for

        query, dict: a query ready to hit the database, i.e. translated as neccessary (see translate_query())

    Output:

        a plotly Figure with the xy data
    '''

    # get all the deisred columns in the given query
    # remove any filter directives in the keys, which are all prefixed by double underscore
    desired_columns = {k.split("__")[0] for k in query.keys()}

    # append year and desired metric to set of desired columns
    desired_columns.add("Year")
    desired_columns.add(efficiency_metric)

    agg_query = AggEtaPFU.objects.filter(**query).values(*desired_columns).query

    with Silent():
        df = pd_sql.read_sql_query(
            str(agg_query), con=connection.cursor().connection)

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

    # Get the sparse matrix representation
    # i, j, x for row, column, value
    # in 3-tuples
    sparse_matrix = (
        PSUT.objects
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
    row_labels = [Translator.index_reverse_translate(i) for i in rows]
    col_labels = [Translator.index_reverse_translate(i) for i in cols]
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


COLUMNS = ["Dataset", "Country", "Method", "EnergyType", "LastStage", "IEAMW", "IncludesNEU", "Year", "ChoppedMat", "ChoppedVar", "ProductAggregation", "IndustryAggregation", "matname", "i", "j", "x"]
def get_csv_from_query(query: dict, columns = COLUMNS):
    db_query = PSUT.objects.filter(**query).values(*columns).query

    with Silent():
        df = pd_sql.read_sql_query(str(db_query), con=connection.cursor().connection)

    # index false to not have column of row numbers
    return df.to_csv(index=False)

def get_excel_from_query(query: dict, columns = COLUMNS):
    db_query = PSUT.objects.filter(**query).values(*columns).query

    with Silent():
        df = pd_sql.read_sql_query(str(db_query), con=connection.cursor().connection)

    # index false to not have column of row numbers
    return df.to_excel(index=False)

class Translator():
    '''Contains the tools for translating PSUT metadata

    Translations go from human readable name -> integer representation in the PSUT table

    Reverse translations go from integer representation -> human readable name
    '''

    __index_translations = None
    __index_reverse_translations = None
    __country_translations = None
    __method_translations = None
    __energytype_translations = None
    __laststage_translations = None
    __IEAMW_translations = None
    __matname_translations = None
    __dataset_translations = None
    __productaggregation_translations = None

    @staticmethod
    def index_translate(name: str) -> int:
        if Translator.__index_translations == None:
            indexes = Index.objects.values_list("IndexID", "Index")
            # get both regular and reverse to limit queries
            Translator.__index_translations = {
                name: id for id, name in indexes}
            Translator.__index_reverse_translations = {
                id: name for id, name in indexes}

        return Translator.__index_translations[name]

    @staticmethod
    def index_reverse_translate(number: int) -> str:
        if Translator.__index_reverse_translations == None:
            indexes = Index.objects.values_list("IndexID", "Index")
            # get both regular and reverse to limit queries
            Translator.__index_translations = {
                name: id for id, name in indexes}
            Translator.__index_reverse_translations = {
                id: name for id, name in indexes}

        return Translator.__index_reverse_translations[number]

    @staticmethod
    def dataset_translate(name: str) -> int:
        if Translator.__dataset_translations == None:
            datasets = Dataset.objects.values_list("DatasetID", "Dataset")
            Translator.__dataset_translations = {
                name: id for id, name in datasets}

        return Translator.__dataset_translations[name]

    @staticmethod
    def get_datasets() -> list[str]:
        if Translator.__dataset_translations == None:
            datasets = Dataset.objects.values_list("DatasetID", "Dataset")
            Translator.__dataset_translations = {
                name: id for id, name in datasets}

        return list(Translator.__dataset_translations.keys())

    @staticmethod
    def country_translate(name: str) -> int:
        if Translator.__country_translations == None:
            countries = Country.objects.values_list("CountryID", "FullName")
            Translator.__country_translations = {
                name: id for id, name in countries}

        return Translator.__country_translations[name]

    @staticmethod
    def get_countries() -> list[str]:
        if Translator.__country_translations == None:
            countries = Country.objects.values_list("CountryID", "FullName")
            Translator.__country_translations = {
                name: id for id, name in countries}

        return list(Translator.__country_translations.keys())

    @staticmethod
    def method_translate(name: str) -> int:
        if Translator.__method_translations == None:
            methods = Method.objects.values_list("MethodID", "Method")
            Translator.__method_translations = {
                name: id for id, name in methods}

        return Translator.__method_translations[name]

    @staticmethod
    def get_methods() -> list[str]:
        if Translator.__method_translations == None:
            methods = Method.objects.values_list("MethodID", "Method")
            Translator.__method_translations = {
                name: id for id, name in methods}

        return list(Translator.__method_translations.keys())

    @staticmethod
    def energytype_translate(name: str) -> int:
        if Translator.__energytype_translations == None:
            enerytpyes = EnergyType.objects.values_list(
                "EnergyTypeID", "EnergyType")
            Translator.__energytype_translations = {
                name: id for id, name in enerytpyes}

        return Translator.__energytype_translations[name]

    @staticmethod
    def get_energytypes() -> list[str]:
        if Translator.__energytype_translations == None:
            enerytpyes = EnergyType.objects.values_list(
                "EnergyTypeID", "EnergyType")
            Translator.__energytype_translations = {
                name: id for id, name in enerytpyes}

        return list(Translator.__energytype_translations.keys())

    @staticmethod
    def laststage_translate(name: str) -> int:
        if Translator.__laststage_translations == None:
            laststages = LastStage.objects.values_list(
                "ECCStageID", "ECCStage")
            Translator.__laststage_translations = {
                name: id for id, name in laststages}

        return Translator.__laststage_translations[name]

    @staticmethod
    def get_laststages() -> list[str]:
        if Translator.__laststage_translations == None:
            laststages = LastStage.objects.values_list(
                "ECCStageID", "ECCStage")
            Translator.__laststage_translations = {
                name: id for id, name in laststages}

        return list(Translator.__laststage_translations.keys())

    @staticmethod
    def ieamw_translate(name: str) -> int:
        if Translator.__IEAMW_translations == None:
            IEAMWs = IEAMW.objects.values_list("IEAMWID", "IEAMW")
            Translator.__IEAMW_translations = {name: id for id, name in IEAMWs}

        return Translator.__IEAMW_translations[name]

    @staticmethod
    def get_ieamws() -> list[str]:
        if Translator.__IEAMW_translations == None:
            IEAMWs = IEAMW.objects.values_list("IEAMWID", "IEAMW")
            Translator.__IEAMW_translations = {name: id for id, name in IEAMWs}

        return list(Translator.__IEAMW_translations.keys())

    @staticmethod
    def includesNEU_translate(name: bool) -> int:
        return int(name)

    @staticmethod
    def get_includesNEUs() -> list[str]:
        return ["True", "False"]

    @staticmethod
    def agglevel_translate(name: str) -> int:
        if Translator.__productaggregation_translations == None:
            productaggregations = AggLevel.objects.values_list(
                "AggLevelID", "AggLevel")
            Translator.__productaggregation_translations = {
                name: id for id, name in productaggregations}

        return Translator.__productaggregation_translations[name]

    @staticmethod
    def get_agglevels() -> list[str]:
        if Translator.__productaggregation_translations == None:
            productaggregations = AggLevel.objects.values_list(
                "AggLevelID", "AggLevel")
            Translator.__productaggregation_translations = {
                name: id for id, name in productaggregations}

        return list(Translator.__productaggregation_translations.keys())

    @staticmethod
    def matname_translate(name: str) -> int:
        if Translator.__matname_translations == None:
            matnames = matname.objects.values_list("matnameID", "matname")
            Translator.__matname_translations = {
                name: id for id, name in matnames}

        return Translator.__matname_translations[name]

    @staticmethod
    def get_matnames() -> list[str]:
        if Translator.__matname_translations == None:
            matnames = matname.objects.values_list("matnameID", "matname")
            Translator.__matname_translations = {
                name: id for id, name in matnames}

        return list(Translator.__matname_translations.keys())

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
        if cls.instance == None:
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
