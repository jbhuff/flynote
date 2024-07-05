from django.contrib import admin
from flynote import models
# Register your models here.

admin.site.register(models.Aircraft)
admin.site.register(models.User_to_aircraft)
admin.site.register(models.Logitem)
admin.site.register(models.Flightlogitem)
admin.site.register(models.Maintlogitem)
admin.site.register(models.Airfield_to_uta)
admin.site.register(models.wandb_item)
admin.site.register(models.wandb_category)
admin.site.register(models.Ac_item)
admin.site.register(models.Ac_value)
admin.site.register(models.Ac_category)
#admin.site.register(models.AD)
admin.site.register(models.AD_aircraft)
admin.site.register(models.wandb_box_segment)
admin.site.register(models.Runway)
#Admin site doesn't allow nulls for some reason
admin.site.register(models.Airfield)
admin.site.register(models.Minimums)
admin.site.register(models.config)
admin.site.register(models.waypoint)
