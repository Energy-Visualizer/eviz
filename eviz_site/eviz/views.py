from django.http import HttpResponse
from eviz.models import PSUT
from django.shortcuts import render

def eviz_index(request):

    # Get 10 PSUT rows from db
    rows = PSUT.objects.values("Year", "i", "j", "x", "Country").filter(Country=155, Year__lt=2015)[:10]


    context = { "psut_rows": rows }

    return render(request, "./test.html", context)