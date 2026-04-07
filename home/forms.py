from django import forms


class DiabetesForm(forms.Form):
    pregnancies = forms.FloatField(required=True, min_value=0, max_value=20)
    glucose = forms.FloatField(required=True, min_value=10, max_value=500)
    bloodpressure = forms.FloatField(required=True, min_value=20, max_value=300)
    skinthickness = forms.FloatField(required=True, min_value=0, max_value=100)
    bmi = forms.FloatField(required=True, min_value=10, max_value=100)
    insulin = forms.FloatField(required=True, min_value=0, max_value=1000)
    pedigree = forms.FloatField(required=True, min_value=0.01, max_value=4.0)
    age = forms.FloatField(required=True, min_value=1, max_value=120)

class BreastCancerForm(forms.Form):
    radius = forms.FloatField(required=True, min_value=5.0, max_value=40.0)
    texture = forms.FloatField(required=True, min_value=5.0, max_value=50.0)
    perimeter = forms.FloatField(required=True, min_value=30.0, max_value=250.0)
    area = forms.FloatField(required=True, min_value=100.0, max_value=3000.0)
    smoothness = forms.FloatField(required=True, min_value=0.01, max_value=0.3)

class HeartDiseaseForm(forms.Form):
    age = forms.FloatField(required=True, min_value=1, max_value=120)
    sex = forms.FloatField(required=True, min_value=0, max_value=1)
    cp = forms.FloatField(required=True, min_value=0, max_value=3)
    trestbps = forms.FloatField(required=True, min_value=50, max_value=300)
    chol = forms.FloatField(required=True, min_value=50, max_value=600)
    fbs = forms.FloatField(required=True, min_value=0, max_value=1)
    restecg = forms.FloatField(required=True, min_value=0, max_value=2)
    thalach = forms.FloatField(required=True, min_value=50, max_value=250)
    exang = forms.FloatField(required=True, min_value=0, max_value=1)
    oldpeak = forms.FloatField(required=True, min_value=0.0, max_value=10.0)
    slope = forms.FloatField(required=True, min_value=0, max_value=2)
    ca = forms.FloatField(required=True, min_value=0, max_value=4)
    thal = forms.FloatField(required=True, min_value=0, max_value=3)

class KidneyDiseaseForm(forms.Form):
    serum_creatinine = forms.FloatField(required=True, min_value=0.1, max_value=20.0)
    blood_urea = forms.FloatField(required=True, min_value=5.0, max_value=400.0)
    albumin = forms.FloatField(required=True, min_value=0, max_value=5)
    hemoglobin = forms.FloatField(required=True, min_value=2.0, max_value=25.0)
    specific_gravity = forms.FloatField(required=True, min_value=1.000, max_value=1.040)
    hypertension = forms.FloatField(required=True, min_value=0, max_value=1)


class PneumoniaUploadForm(forms.Form):
    xray = forms.ImageField(required=True)
