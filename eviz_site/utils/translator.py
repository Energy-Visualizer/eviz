# translator.py contains the functionality to quickly translate PSUT values
# to and from human readable form and numerical database form
#
# Authors: Kenny Howes - kmh67@calvin.edu
#          Edom Maru
##################################################

from bidict import bidict
from django.apps import apps
from eviz.models import PSUT

from datetime import datetime, timedelta

# how long to cache information from the database 
# in *hours*
TRANSLATOR_CACHE_TTL = 24

class Translator:
    # A dictionary where keys are model names and values are tuples
    # of date times and bidict objects
    __translations = {}

    __cache_ttl = timedelta(hours=TRANSLATOR_CACHE_TTL)

    def __init__(self, database: str):
        self._db = database

    @staticmethod
    def __load_bidict(model_name: str, id_field: str, name_field: str, database: str) -> bidict:
        """
        Load translations for a specific model if not already loaded.
        
        Args:
            model_name (str): The name of the model to load translations for.
            id_field (str): The name of the ID field in the model.
            name_field (str): The name of the field containing the human-readable name.
        
        Returns:
            bidict: A bidirectional dictionary of translations for the model.
        """

        # check if we have the desired information
        if (database + ":" + model_name) not in Translator.__translations:
            Translator.__load_and_cache(model_name, id_field, name_field, database)
        
        model_translations = Translator.__translations[database + ":" + model_name]
        
        # if the data's cache ttl is expired,
        # recache and reload
        if (datetime.today().date() - model_translations[0]) > Translator.__cache_ttl:
            Translator.__load_and_cache(model_name, id_field, name_field, database)
            model_translations = Translator.__translations[database + ":" + model_name]
            
        return model_translations[1]
    
    @staticmethod
    def __load_and_cache(model_name: str, id_field: str, name_field: str, database: str):

        # Get the model class dynamically
        model = apps.get_model(app_label='eviz', model_name=model_name)

        # Create a bidict with name:id pairs
        Translator.__translations[database + ":" + model_name] = (
            # a datetime to see how long this has been cached
            datetime.today().date(),
            # the bidict containing all the data information
            bidict(
                {getattr(item, name_field): getattr(item, id_field) for item in model.objects.using(database).all()}
            )
        )

    def _translate(self, model_name, value, id_field, name_field):
        # Translate a value between its ID and name for a specific model.
        # value: The value to translate (can be either an ID or a name).
        # Returns: The translated value (either ID or name, depending on input).
        translations = self.__load_bidict(model_name, id_field, name_field, self._db)
        
        # try to get the translation
        if translation := translations.get(value) or translations.inverse.get(value):
            return translation
        
        # if no translation found
        raise KeyError("Unrecognized key '" + value + "' for " + model_name)

    # The following methods are specific translation functions for different models
    # They all use the _translate method with appropriate parameters
    def index_translate(self, value):
        return self._translate('Index', value, 'IndexID', 'Index')

    def dataset_translate(self, value):
        return self._translate('Dataset', value, 'DatasetID', 'Dataset')

    def country_translate(self, value):
        return self._translate('Country', value, 'CountryID', 'FullName')

    def method_translate(self, value):
        return self._translate('Method', value, 'MethodID', 'Method')

    def energytype_translate(self, value):
        return self._translate('EnergyType', value, 'EnergyTypeID', 'FullName')

    def laststage_translate(self, value):
        return self._translate('LastStage', value, 'ECCStageID', 'ECCStage')

    def ieamw_translate(self, value):
        return self._translate('IEAMW', value, 'IEAMWID', 'IEAMW')

    def matname_translate(self, value):
        return self._translate('matname', value, 'matnameID', 'matname')
    
    def grossnet_translate(self, value):
        return self._translate('GrossNet', value, 'GrossNetID', 'GrossNet')

    def agglevel_translate(self, value):
        return self._translate('AggLevel', value, 'AggLevelID', 'AggLevel')

    def includesNEU_translate(self, value):
        return int(value) if isinstance(value, bool) else int(bool(value))

    @staticmethod
    def get_all(attribute, database = "default"):
        """
        Get all possible values for a given attribute.
        
        Inputs:
            attribute (str): The name of the attribute to get values for.
        
        Outputs:
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
            'grossnet': ('GrossNet', 'GrossNetID', 'GrossNet'),
        }
        
        if attribute not in model_mappings:
            raise ValueError(f"Unknown attribute: {attribute}")
        
        # Get model details and load translations
        model_name, id_field, name_field = model_mappings[attribute]
        translations = Translator.__load_bidict(model_name, id_field, name_field, database)
        return list(translations.keys())
    
    @staticmethod
    def get_includesNEUs(self):
        return [True, False]

    # TODO: This needs to be finished...
    @staticmethod
    def get_all_available(attribute):
        """Get all available values for a given attribute from the PSUT model.
        
        Inputs:
            attribute (str): The name of the attribute to get values for.
        
        Outputs:
            A list of distinct values for the attribute from the PSUT model.
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
            'grossnet': ('GrossNet', 'GrossNetID', 'GrossNet'),
        }
        
        if attribute not in model_mappings:
            raise ValueError(f"Unknown attribute: {attribute}")
        
        model_name, id_field, name_field = model_mappings[attribute]
        translations = Translator.__load_bidict(model_name, id_field, name_field)

        # Print distinct values for the attribute from the PSUT model
        # print(PSUT.objects.order_by().values_list(model_name, flat=True).distinct())