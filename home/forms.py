from django import forms

class DiabetesForm(forms.Form):
    pregnancies = forms.FloatField(required=True)
    glucose = forms.FloatField(required=True)
    bloodpressure = forms.FloatField(required=True)
    skinthickness = forms.FloatField(required=True)
    bmi = forms.FloatField(required=True)
    insulin = forms.FloatField(required=True)
    pedigree = forms.FloatField(required=True)
    age = forms.FloatField(required=True)

class BreastCancerForm(forms.Form):
    radius = forms.FloatField(required=True)
    texture = forms.FloatField(required=True)
    perimeter = forms.FloatField(required=True)
    area = forms.FloatField(required=True)
    smoothness = forms.FloatField(required=True)

class HeartDiseaseForm(forms.Form):
    age = forms.FloatField(required=True)
    sex = forms.FloatField(required=True)
    cp = forms.FloatField(required=True)
    trestbps = forms.FloatField(required=True)
    chol = forms.FloatField(required=True)
    fbs = forms.FloatField(required=True)
    restecg = forms.FloatField(required=True)
    thalach = forms.FloatField(required=True)
    exang = forms.FloatField(required=True)
    oldpeak = forms.FloatField(required=True)
    slope = forms.FloatField(required=True)
    ca = forms.FloatField(required=True)
    thal = forms.FloatField(required=True)

class KidneyDiseaseForm(forms.Form):
    serum_creatinine = forms.FloatField(required=True)
    blood_urea = forms.FloatField(required=True)
    albumin = forms.FloatField(required=True)
    hemoglobin = forms.FloatField(required=True)
    specific_gravity = forms.FloatField(required=True)
    hypertension = forms.FloatField(required=True)
