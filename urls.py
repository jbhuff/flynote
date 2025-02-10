from django.urls import path, register_converter
from .views import (home, dash, show_ac, wandb, show_fl, add_ad, add_ad_ac, show_ad_ac
                    , show_ads, update_ad, add_ad_to_ac, show_flights, show_maint, add_maint,
                    show_maint_item, show_ada_mli, add_file_maint_item, get_file, 
                    create_ttaf_adjust, update_wandb, add_wandb_image, convert_coordinates,
                    show_waypoint, show_squawk, squawk_quick_add, attach_mlog_to_squawk, delete_squawk
        )


urlpatterns = [
            path('', home, name='home'),
            path('hello/<str:msg>', home, name='hello'),
            path('dash', dash, name='dashboard'),
            path('convert_coordinates', convert_coordinates, name='convert_coordinates'),
            #path('check_crosswind', check_crosswind, name='check_crosswind'),
            path('aircraft/<int:ptr>', show_ac, name='show_ac'),
            path('squawk_quick_add/<int:aircraft_id>', squawk_quick_add, name='squawk_quick_add'),
            path('wandb/<int:ptr>', wandb, name='wandb'),
            path('update_wandb/<int:ptr>', update_wandb, name='update_wandb'),
            path('add_wandb_image/<int:ptr>', add_wandb_image, name='add_wandb_image'),
            path('show_fl/<int:ptr>', show_fl, name='show_fl'),
            path('show_waypoint/<int:wp_id>', show_waypoint, name='show_waypoint'),
            path('show_squawk/<int:squawk_id>', show_squawk, name='show_squawk'),
            path('add_ad/', add_ad, name='add_ad'),
            path('add_ad_ac/', add_ad_ac, name='add_ad_ac'),
            path('show_ad_ac/<int:ptr>', show_ad_ac, name='show_ad_ac'),
            path('show_maint/<int:ptr>', show_maint, name='show_maint'),
            path('create_ttaf_adjust/<int:ptr>', create_ttaf_adjust, name='create_ttaf_adjust'),
            path('show_ada_mli/<int:ptr>', show_ada_mli, name='show_ada_mli'),
            path('get_file/<int:ptr>', get_file, name='get_file'),
            path('add_file_maint_item/<int:ptr>', add_file_maint_item, name='add_file_maint_item'),
            path('show_maint_item/<int:ptr>', show_maint_item, name='show_maint_item'),
            path('show_ads/<int:ptr>', show_ads, name='show_ads'),
            path('show_flights/<int:ptr>', show_flights, name='show_flights'),
            path('add_maint/<int:ptr>', add_maint, name='add_maint'),
            path('update_ad/<int:ad_ptr>/<int:ad_ac_ptr>', update_ad, name='update_ad'),
            path('add_ad_to_ac/<int:ad_ptr>/<int:ac_ptr>', add_ad_to_ac, name='add_ad_to_ac'),
            path('attach_mlog_to_squawk/<int:mlog_id>', attach_mlog_to_squawk, name='attach_mlog_to_squawk'),
            path('delete_squawk/<int:sq_ptr>', delete_squawk, name='delete_squawk'),
            
            ]
