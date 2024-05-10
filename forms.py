from .models import Logitem, User_to_aircraft, Aircraft, AD, Maintlogitem, AD_aircraft, Ada_maintitem
from django import forms

#Eli comment

class Quicklog(forms.Form):
    note = forms.CharField(max_length=2000)

class Flightlog(forms.Form):
    date = forms.DateField()
    note = forms.CharField(max_length=2000)
    tach = forms.FloatField()
    hours = forms.FloatField()
    fuel = forms.FloatField(required=False)
    day_landings = forms.IntegerField()
    night_landings = forms.IntegerField(required=False)

class logform(forms.Form):
    date = forms.DateField()
    note = forms.CharField(widget=forms.Textarea)

class Maintlogform(logform):
    tach = forms.CharField(max_length=10)
    oil_changed = forms.BooleanField(required=False)
    annual_finished = forms.BooleanField(required=False)

class Ad_form(forms.Form):
    number = forms.CharField()
    description = forms.CharField(widget=forms.Textarea)
    superseded_by = forms.ModelChoiceField(queryset=AD.objects.all(), required=False)

class ad_aircraft_form(forms.Form):
    ad = forms.ModelChoiceField(queryset=AD.objects.all())
    aircraft = forms.ModelChoiceField(queryset=Aircraft.objects.all())
    due_tach = forms.FloatField(required=False)
    due_date = forms.DateField(required=False)
    complied = forms.BooleanField(required=False)
    compliance_log_item = forms.ModelChoiceField(queryset=Maintlogitem.objects.all(), required=False)
    recurring = forms.BooleanField(required=False)
    applicable = forms.BooleanField(required=False)

class ad_aircraft_mform_off(forms.ModelForm):
    class Meta:
        model = AD_aircraft
        fields = [ 'ad', 'aircraft', 'due_tach', 'due_date', 'complied', 'compliance_log_item',
                'recurring', 'applicable', 'note' ]
    def __init__(self, *args, **kwargs):
        super(ad_aircraft_mform, self).__init__(*args, **kwargs)
        self.fields['due_tach'].required = False
        self.fields['due_date'].required = False
        self.fields['compliance_log_item'].required = False

class ad_aircraft_mform(forms.ModelForm):
    class Meta:
        model = AD_aircraft
        fields = "__all__"

class ad_mform(forms.ModelForm):
    class Meta:
        model = AD
        fields = "__all__"
        widgets = {
                'description': forms.Textarea(attrs={'cols':50, 'rows': 10}),
                }

class ad_quickpick(forms.Form):
    ada = forms.ModelChoiceField(queryset=AD_aircraft.objects.all())

class Ada_maint_form(forms.ModelForm):
    class Meta:
        model = Ada_maintitem
        fields = "__all__"

class Crosswind_form(forms.Form):
    wind = forms.CharField(max_length=5)
    runway = forms.CharField(max_length=2)

class Airfield_form(forms.Form):
    airfield = forms.CharField(max_length=4)

class LoginForm(forms.Form):
    username = forms.CharField(label='Username')
    password = forms.CharField(label='Password', widget=forms.PasswordInput)

class UploadFileForm(forms.Form):
    title = forms.CharField(max_length=50, required=False, help_text='Optional')
    file = forms.FileField()

class tach_adjust_form(forms.Form):
    hours = forms.FloatField(help_text="Enter tach hours of the removed tach")
