from django.db import models
from django.contrib.auth.models import User as DjangoUser

class Dataset(models.Model):
    """ Model representing a database table named 'Dataset'."""
    DatasetID = models.PositiveSmallIntegerField(primary_key=True)
    Dataset = models.TextField()
    FullName = models.TextField()
    Description = models.TextField()

    class Meta:
        db_table = "Dataset"
        managed = False # Django won't manage these tables
        
class Country(models.Model):
    """ Model representing a database table named 'Country'."""
    CountryID = models.PositiveSmallIntegerField(primary_key=True)
    Country = models.TextField()
    FullName = models.TextField()
    Description = models.TextField()
    IsCountry = models.BooleanField()
    IsAggregation = models.BooleanField()
    IsContinent = models.BooleanField()
    class Meta:
        db_table = "Country"
        managed = False

class Method(models.Model):
    """ Model representing a database table named 'Method'."""
    MethodID = models.PositiveSmallIntegerField(primary_key=True)
    Method = models.TextField()
    FullName = models.TextField()
    Description = models.TextField()
    class Meta:
        db_table = "Method"
        managed = False
    
class EnergyType(models.Model):
    """ Model representing a database table named 'EnergyType'."""
    EnergyTypeID = models.PositiveSmallIntegerField(primary_key=True)
    EnergyType = models.TextField()
    FullName = models.TextField()
    Description = models.TextField()
    class Meta:
        db_table = "EnergyType"
        managed = False

class LastStage(models.Model):
    """ Model representing a database table named 'LastStage'."""
    ECCStageID = models.PositiveSmallIntegerField(primary_key=True)
    ECCStage = models.TextField()
    FullName = models.TextField()
    Description = models.TextField()
    class Meta:
        db_table = "ECCStage"
        managed = False
    
class IEAMW(models.Model):
    """ Model representing a database table named 'IEAMW'."""
    IEAMWID = models.PositiveSmallIntegerField(primary_key=True)
    IEAMW = models.TextField()
    FullName = models.TextField()
    Description = models.TextField()
    class Meta:
        db_table = "IEAMW"
        managed = False

class IncludesNEU(models.Model):
    """ Model representing a database table named 'IncludesNEU'."""
    IncludesNEUID = models.PositiveSmallIntegerField(primary_key=True)
    IncludesNEU = models.BooleanField()
    FullName = models.TextField()
    Description = models.TextField()
    class Meta:
        db_table = "IncludesNEU"
        managed = False

class Year(models.Model):
    """ Model representing a database table named 'Year'."""
    YearID = models.PositiveSmallIntegerField(primary_key=True)
    Year = models.PositiveSmallIntegerField()
    class Meta:
        db_table = "Year"
        managed = False
        
class AggLevel(models.Model):
    """ Model representing a database table named 'AggLevel'."""
    AggLevelID = models.PositiveSmallIntegerField(primary_key=True)
    AggLevel = models.TextField()
    FullName = models.TextField()
    Description = models.TextField()
    class Meta:
        db_table = "AggLevel"
        managed = False

class matname(models.Model):
    """ Model representing a database table named 'matname'."""
    matnameID = models.PositiveSmallIntegerField(primary_key=True)
    matname = models.TextField()
    FullName = models.TextField()
    Description = models.TextField()
    class Meta:
        db_table = "matname"
        managed = False

class GrossNet(models.Model):
    """ Model representing a database table named 'GrossNet'."""
    GrossNetID = models.PositiveSmallIntegerField(primary_key=True)
    GrossNet = models.TextField()
    FullName = models.TextField()
    Description = models.TextField()
    class Meta:
        db_table = "GrossNet"
        managed = False

        
class Index(models.Model):
    """ Model representing a database table named 'Index'."""
    IndexID = models.PositiveSmallIntegerField(primary_key=True)
    Index = models.TextField()
    class Meta:
        db_table = "Index"
        managed = False
        

class PSUT(models.Model):
    """ Model representing a datatbase table named 'PSUT'."""
    # define meta attributes
    class Meta:
        db_table = "PSUTReAllChopAllDsAllGrAll"
        managed = False

    Dataset = models.PositiveSmallIntegerField()
    Country = models.PositiveSmallIntegerField()
    Method = models.PositiveSmallIntegerField()
    EnergyType = models.PositiveSmallIntegerField()
    LastStage = models.PositiveSmallIntegerField()
    IEAMW = models.PositiveSmallIntegerField()
    IncludesNEU = models.PositiveSmallIntegerField()
    Year = models.PositiveSmallIntegerField()
    ChoppedMat = models.PositiveSmallIntegerField()
    ChoppedVar = models.PositiveSmallIntegerField()
    ProductAggregation = models.PositiveSmallIntegerField()
    IndustryAggregation = models.PositiveSmallIntegerField()
    matname = models.PositiveSmallIntegerField()
    i = models.PositiveSmallIntegerField()
    j = models.PositiveSmallIntegerField()
    x = models.FloatField()

class AggEtaPFU(models.Model):
    """ Model representing a database table named 'AggEtaPFU'."""
    class Meta:
        db_table = "AggEtaPFU"
        managed = False

    Dataset = models.PositiveSmallIntegerField()
    Country = models.PositiveSmallIntegerField()
    Method = models.PositiveSmallIntegerField()
    EnergyType = models.PositiveSmallIntegerField()
    LastStage = models.PositiveSmallIntegerField()
    IEAMW = models.PositiveSmallIntegerField()
    IncludesNEU = models.PositiveSmallIntegerField()
    Year = models.PositiveSmallIntegerField()
    ChoppedMat = models.PositiveSmallIntegerField()
    ChoppedVar = models.PositiveSmallIntegerField()
    ProductAggregation = models.PositiveSmallIntegerField()
    IndustryAggregation = models.PositiveSmallIntegerField()
    GrossNet = models.PositiveSmallIntegerField()
    EXp = models.FloatField()
    EXf = models.FloatField()
    EXu = models.FloatField()
    etapf = models.FloatField()
    etafu = models.FloatField()
    etapu = models.FloatField()
    
class EvizUser(DjangoUser):
    """ Model representing a database table named 'EvizUser'."""
    institution = models.CharField(max_length=255)
    country = models.CharField(max_length=255)

class EmailAuthCodes(models.Model):
    """ Model for storing email auhtentication codes and associated account information."""
    code = models.TextField(max_length=255)
    account_info = models.BinaryField()