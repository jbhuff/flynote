from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model

# Create your models here.
User = get_user_model()

class Aircraft(models.Model):
    name = models.CharField(max_length=200)
    make = models.CharField(max_length=200)
    model = models.CharField(max_length=200)
    year = models.IntegerField()

    def __str__(self):
        return self.name

class User_to_aircraft(models.Model):
    aircraft = models.ForeignKey(Aircraft, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.user) + " " + str(self.aircraft)

class Minimums(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    visibility = models.IntegerField(default=5)
    ceiling = models.IntegerField(default=3000)
    wind = models.IntegerField(default=16)
    crosswind = models.IntegerField(default=8)
    takeoff_mult = models.IntegerField(default=2)
    landing_mult = models.IntegerField(default=2)

class Logitem(models.Model):
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    date = models.DateField()
    uta = models.ForeignKey(User_to_aircraft, null=True, on_delete=models.SET_NULL)
    logtype = models.CharField(max_length=50)
    note = models.CharField(max_length=2000)

    def __str__(self):
        return str(self.created_at.date()) + ' ' + self.logtype + ' ' + self.note[:14] + '...'

class Flightlogitem(models.Model):
    tach = models.CharField(max_length=10)
    note = models.CharField(max_length=2000)
    hours = models.CharField(max_length=5)
    fuel = models.CharField(max_length=5, null=True)
    logitem = models.ForeignKey(Logitem, on_delete=models.CASCADE)
    night_landings = models.IntegerField(default=0)
    day_landings = models.IntegerField(default=1)
    bfr_complete = models.BooleanField(default=False)
    def __str__(self):
        return str(self.logitem.date) + ' ' + str(self.note)

class Maintlogitem(models.Model):
    tach = models.CharField(max_length=10)
    logitem = models.ForeignKey(Logitem, on_delete=models.CASCADE)
    oil_changed = models.BooleanField(default=False)
    date = models.DateField()
    annual_finished = models.BooleanField(default=False)
    transponder_certified = models.BooleanField(default=False)
    pitot_static_certified = models.BooleanField(default=False)

    def __str__(self):
        return str(self.date) + ' ' + self.tach 


class Airfield(models.Model):
    #uta = models.ForeignKey(User_to_aircraft, null=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=100, null=True)
    k_id = models.CharField(max_length=4)
    field_elevation = models.IntegerField()
    pattern_altitude = models.IntegerField()

    def __str__(self):
        return self.k_id + ": " + self.name

class Airfield_to_uta(models.Model):
    airfield = models.ForeignKey(Airfield, on_delete=models.CASCADE)
    uta = models.ForeignKey(User_to_aircraft, null=True, on_delete=models.CASCADE)

class Runway(models.Model):
    airfield = models.ForeignKey(Airfield, on_delete=models.CASCADE)
    heading = models.IntegerField()

class wandb_category(models.Model):
    name = models.CharField(max_length=40)
    aircraft = models.ForeignKey(Aircraft, on_delete=models.CASCADE)
    arm = models.FloatField()

    def __str__(self):
        return self.aircraft.name + " " + self.name

class wandb_item(models.Model):
    name = models.CharField(max_length=40)
    weight = models.IntegerField(null=True)
    category = models.ForeignKey(wandb_category, on_delete=models.CASCADE)
    
    def __str__(self):
        return self.name + " " + self.category.name

    def moment(self):
        return round(self.weight * self.category.arm, 2)

class wandb_box_segment(models.Model):
    aircraft = models.ForeignKey(Aircraft, on_delete=models.CASCADE)
    min_cg = models.FloatField()
    max_cg = models.FloatField()
    gross_weight = models.IntegerField()

    def __str__(self):
        return "{} {}: {} to {}".format(self.aircraft, self.gross_weight, self.min_cg, self.max_cg)

class Ac_category(models.Model):
    name = models.CharField(max_length=200)
            
    def __str__(self):
        return self.name

class Ac_item(models.Model):
    aircraft = models.ForeignKey(Aircraft, on_delete=models.CASCADE)
    category = models.ForeignKey(Ac_category, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.aircraft) + " " + str(self.category)

class Ac_value(models.Model):
    ac_item = models.ForeignKey(Ac_item, on_delete=models.CASCADE)
    value = models.CharField(max_length=200)

    def __str__(self):
        return str(self.ac_item) + " value: " + self.value

class AD(models.Model):
    number = models.CharField(max_length=50)
    description = models.CharField(max_length=500)
    superseded_by = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True)
    url = models.CharField(max_length=500, null=True, blank=True)
    def __str__(self):
        return self.number

class AD_aircraft(models.Model):
    ad = models.ForeignKey(AD, on_delete=models.CASCADE)
    aircraft = models.ForeignKey(Aircraft, on_delete=models.CASCADE)
    due_tach = models.FloatField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    complied = models.BooleanField(default=False, blank=True)
    compliance_log_item = models.ForeignKey(Maintlogitem, null=True, blank=True, on_delete=models.SET_NULL)
    recurring = models.BooleanField(default=False, blank=True)
    note = models.CharField(max_length=400, null=True, blank=True)
    #applicable = models.BooleanField(default=True, blank=True)
    applicable = models.BooleanField()
    warning = models.BooleanField(default=False, blank=True)
    def __str__(self):
        return self.ad.number

class Ada_maintitem(models.Model):
    ada = models.ForeignKey(AD_aircraft, on_delete=models.CASCADE)
    maintitem = models.ForeignKey(Maintlogitem, on_delete=models.CASCADE)
    note = models.CharField(max_length=400)

    def __str__(self):
        return str(self.ada) + " " + str(self.maintitem)

class File(models.Model):
    name = models.CharField(max_length=200)
    rel_path = models.CharField(max_length=400)

    def __str__(self):
        return self.name

class Maintitem_file(models.Model):
    file = models.ForeignKey(File, on_delete=models.CASCADE)
    maintitem = models.ForeignKey(Maintlogitem, on_delete=models.CASCADE)

class Ac_file(models.Model):
    file = models.ForeignKey(File, on_delete=models.CASCADE)
    ac_item = models.ForeignKey(Ac_item, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.ac_item) + " file: " + str(self.file)

class Tach_adjust(models.Model):
    hours = models.FloatField()
    firstlog = models.ForeignKey(Maintlogitem, null=True, on_delete=models.SET_NULL)
    category = models.CharField(max_length=100)

    def __str__(self):
        return self.category + " " + str(self.firstlog.logitem.uta.aircraft) + " " + str(self.hours)

class waypoint(models.Model):
    lat = models.FloatField(blank=True, null=True)
    lon = models.FloatField(blank=True, null=True)
    input_string = models.CharField(max_length=50, blank=True)
    name = models.CharField(max_length=65, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.name + " created: " + str(self.created_at)

class config(models.Model):
    name = models.CharField(max_length=50)
    value = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class squawk(models.Model):
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=200, blank=True)
    aircraft = models.ForeignKey(Aircraft, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    maintenance_log = models.ForeignKey(Maintlogitem, null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return str(self.aircraft) + " " + self.name

class user_config(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    value = models.CharField(max_length=50)

    def __str__(self):
        return "{} {}: {}".format(str(self.user), self.name, self.value)
    
    def __getitem__(self, key):
        return getattr(self, key)