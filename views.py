from django.shortcuts import render, redirect
from django.http import HttpResponse, FileResponse
from django.urls import reverse
from urllib.parse import urlencode
from .models import (Aircraft, User_to_aircraft, Logitem, Flightlogitem, Maintlogitem,
                    Airfield, Airfield_to_uta, wandb_category, wandb_item, Ac_item, 
                    AD, AD_aircraft, Ada_maintitem, File, Maintitem_file, Tach_adjust,
                    Ac_file, Ac_category, Minimums, Runway, waypoint, config, squawk,
                    user_config, Ac_value, Afu_inquiry)
from django.contrib.auth import authenticate
from django.contrib.auth import login as djlogin
from django.contrib.auth import logout as djlogout
from django.contrib.auth.decorators import login_required
from .forms import (Quicklog, Flightlog, Ad_form, ad_aircraft_form, 
                   ad_aircraft_mform, ad_mform, Maintlogform, Maintlogform_v1, ad_quickpick,
                   Ada_maint_form, UploadFileForm, tach_adjust_form, Crosswind_form,
                   LoginForm, Airfield_form, gps_form, waypointForm, gps_from_noregex,
                   quicksquawk, squawkform, squawklistform, mins_form, Fastlog)
import datetime
import json, re
from .helper import ( get_metars, get_wandb, get_gross_weight, get_max_aft_cg, 
        get_tach_log, get_TTE, file_upload, get_path, get_latest_ttaf, get_cg_range,
        get_latest_tach, get_crosswind, decode_metar, get_angle_difference, get_pressure_alt,
        get_density_alt, get_cloudbase, get_dewpoint_int, get_landings, get_currency_deadline,
        get_field_elevation, get_garmin_string, get_gps_regex, add_color, get_med_item, 
        get_metar_hours_back, get_da_color, get_log_item_num, get_oil_color, get_freezing_level, 
        get_td, get_or_put_one_ac_item, get_bfr_deadline, get_or_create_user_item, get_or_create_min_obj,
        add_cal_months, get_distance_tp, get_airport_item, get_pilot_hours_in_last_days)
from django.contrib.auth import get_user_model


# Create your views here.
#comment test
User = get_user_model()


def home(request):
    return HttpResponse("Hello flynote")

@login_required
def dash(request):
    aircraft_rs = User_to_aircraft.objects.filter(user=request.user)
    airfield_to_utas = Airfield_to_uta.objects.filter(uta__in=aircraft_rs)
    metars = []
    mins = get_or_create_min_obj(user=request.user)
    

    pilot_items = [] #passed to template
    af_items = []

    user_items = user_config.objects.filter(user=request.user)
    if len(user_items) == 0:
        user_items = None

    if user_items is not None:
        i = get_med_item(user_items)
    
    if i is not None:
        if i.name == 'Basic Med Complete':    
            notes = "Renewal due in 48 calendar months after completion"
            d = {'name':i.name, 'value':i.value, 'notes':notes}
            pilot_items.append(add_color(d))
            for i in user_items:
                if i.name == "Basic Med Course Complete":
                    notes = "Course retake due in 24 months"
                    d = {'name':i.name, 'value':i.value, 'notes':notes}
                    pilot_items.append(add_color(d))
        elif i.name == 'Class I Complete':
            notes = "Renewal due in 12 calendar months after completion"
            complete_date = datetime.datetime.strptime(i.value, "%Y-%m-%d").date()
            due_date = add_cal_months(complete_date, 12)
            today = datetime.date.today()
            if today > due_date:  #Class I expired.  Now Class II
                due_date = add_cal_months(complete_date, 60)
                notes = 'Medical expired for commercial use. Can still use for PPL and CFI until %s' % due_date
                color = 2
                if today > due_date:  #Class II expired.  Now Class III
                    notes = 'Medical FULLY expired on %s' % due_date
                    color = 1
            else:
                notes = 'Class I Medical expires on %s and reverts to non-commercial use (except CFI) at ' % due_date
            d = {'name':i.name, 'value':i.value, 'notes':notes}
            pilot_items.append(add_color(d, color))
        #Add more Med options here!!



    get_airfield = request.GET.get('airfield', None)    
    last_metar = None
    last_airfield = None
    for ai in Afu_inquiry.objects.filter(user=request.user).order_by('ts'):
        #k_id = aftu.airfield.k_id
        #ms = get_metars(k_id, hours=4)
        #metars.append({'k_id':k_id, 'metar_list':ms})
        #last_metar = ms[0]
        #last_airfield = aftu.airfield
        last_airfield = ai.af
    
    hours_back = get_metar_hours_back(request.user)
    if get_airfield == None:
        if last_airfield == None:
            af = 'KCEU'
        else:
            af = last_airfield
        ms = get_metars(af, hours=hours_back)
        #metars.append({'k_id':af, 'metar_list':ms})
        if len(ms) > 0:
            metar_d = decode_metar(ms[0], ret='dict')
        else:
            metar_d = {}
    else:
        af = get_airfield
        ms = get_metars(af, hours=hours_back)
        #metars.append({'k_id':af, 'metar_list':ms})
        metar_d = decode_metar(ms[0], ret='dict')
    if len(ms) > 0:
        last_metar = ms[0]
    else:
        last_metar = None
    ai = Afu_inquiry(af=af, metar=last_metar, user=request.user)
    ai.save()
    #aqs = Airfield_to_uta.objects.filter(airfield__k_id=af)
    #if len(aqs) < 1:
    afqs = Airfield.objects.filter(k_id=af)
    if len(afqs) < 1:
        fe = get_field_elevation(af)
        afo = Airfield(k_id=af, name=af, field_elevation=fe, pattern_altitude=fe+1000)
        afo.save()
        rws = get_airport_item(afo.k_id, 'runways')
        for this_rw_dict in rws:
            rwp = this_rw_dict['id']
            rwp_list = rwp.split('/')
            for rwh in rwp_list:
                this_rw = Runway(airfield=afo, heading=int(rwh))
                this_rw.save()
    else:
        afo = afqs[0]
    last_airfield = afo        
    xwform = Crosswind_form()
    xw = None
    aform = Airfield_form(initial={'airfield':af})
    next_aform = Airfield_form()

    #currency
    nl = get_landings(request.user, 90, 'night')
    dl = get_landings(request.user, 90, 'day')
    night_current =  (nl >= 3)
    day_current = (dl >= 3)

    d = {'name':"Night Current", 'value':night_current}
    if night_current:
        nc_deadline = get_currency_deadline(request.user, 'night')
        d['notes'] = "deadline: {}".format(nc_deadline)
        d_level = 4
    else:
        nc_deadline = None
        d['notes'] = "deadline passed"
        d_level = 1
    pilot_items.append(add_color(d, d_level))

    d = {'name':"Day Current", 'value':day_current}
    if day_current:
        dc_deadline = get_currency_deadline(request.user, 'day')
        d['notes'] = "deadline: {}".format(dc_deadline)
        d_level = 4
    else:
        dc_deadline = None
        d_level = 1
    pilot_items.append(add_color(d, d_level))
    
    bfr_deadline = get_bfr_deadline(request.user)
    days_remaining_td = bfr_deadline - datetime.date.today()
    days_remaining = days_remaining_td.days
    color = 3
    if days_remaining < 0:
        color = 1
    elif days_remaining < get_or_create_user_item("BFR Warning", 20, request.user):
        color = 2
    pilot_items.append(add_color({'name':"Biannual Flight Review Deadline", 'value':bfr_deadline}, color))
    
    tt = get_or_create_user_item("Pilot Total Time", 50, request.user)
    days = 60
    recent_hours = get_pilot_hours_in_last_days(request.user, days)
    remaining = 1500 - int(tt)
    if remaining > 0:
        per_day = recent_hours['hours__sum'] / 30
        remaining_days = remaining / per_day
        completion_date = datetime.date.today() + datetime.timedelta(int(remaining_days))
        ret_string = "{}".format(completion_date)
        ret_notes = "{} in last {} days".format(round(recent_hours['hours__sum'], 1), days)
    else:
        ret_string = "YOU DID IT"
    pilot_items.append(add_color({'name':"Estimated Date to 1500", 'value':ret_string, 'notes':ret_notes}, 4))

    min_alerts = {}
    if request.method == 'POST':
        form = Crosswind_form(request.POST)
        if form.is_valid():
            wind = form.cleaned_data['wind']
            rw = form.cleaned_data['runway']
    elif 'wind' in metar_d.keys():
        wind = metar_d['wind'][0:5]
        runways = Runway.objects.filter(airfield=last_airfield)
        if len(runways) == 0:
            rw = None
        else:
            rw = int(runways[0].heading)
        wind_angle = wind[0:3]  #also available as a dict item
        angle_diff = get_angle_difference(wind_angle, rw*10)
        for r in runways:
            new_angle_diff = get_angle_difference(wind_angle, int(r.heading)*10)
            if new_angle_diff < angle_diff:
                angle_diff = new_angle_diff
                rw = int(r.heading)
            new_heading = int(r.heading) + 18
            if new_heading > 36:
                new_heading = 36 - new_heading
            new_angle_diff = get_angle_difference(wind_angle, new_heading*10)
            if new_angle_diff < angle_diff:
                angle_diff = new_angle_diff
                rw = new_heading
    else:
        wind = '00000'
        rw = 0
    xw = get_crosswind(wind, int(rw))
            #assert 1==0, "STOP"
    gf = None
    if int(wind[-2:]) >= mins.wind:
        min_alerts['wind'] = True

    color = 4   #Add the crosswind info
    xw_int = int(xw['speed'])
    if  xw_int > mins.crosswind - 5:
        #min_alerts['crosswind'] = True
        color = 2
    if  xw_int > mins.crosswind:
        color = 1
    af_items.append(add_color({'name':"Crosswind", 'value':int(xw['speed'])}, color))

    if xw['direct']:
        af_items.append(add_color({'name':"Crosswind", 'value':"DIRECT"}, 2))


    if 'gusts' in metar_d.keys():
        if int(metar_d['gusts']) >= mins.wind:
            min_alerts['wind'] = True
        gf = int(metar_d['gusts']) - int(metar_d['wind_speed'])
    #fe = int(last_airfield.field_elevation)
    fe = get_field_elevation(af)

    if 'dewpoint' in metar_d.keys():
        dp = get_dewpoint_int(metar_d['dewpoint'])
    else:
        dp = None
    af_items.append(add_color({'name':"Dewpoint", 'value':dp}))

    condition = "UNKNOWN"
    if isinstance(fe, int):
        af_items.append(add_color({'name':"Field Elevation", 'value':fe}))
            
        if 'altimeter' in metar_d.keys():
            pa = get_pressure_alt(fe, metar_d['altimeter'][1:])
        else:
            pa = None

        af_items.append(add_color({'name':"Pressure Altitude", 'value':pa}))

        if 'temp' in metar_d.keys():
            da = get_density_alt(pa, metar_d['temp'])
            est_cloudbase = get_cloudbase(metar_d['temp'], dp) + fe
            fl = get_freezing_level(fe, metar_d['temp'])
            cb = metar_d['lowest_ceiling']
        else:
            da = 0
            est_cloudbase = None
            cb = None
            fl = 0

        color = get_da_color(da, request.user)
        af_items.append(add_color({'name':"Density Altitude", 'value':da}, color))
        af_items.append(add_color({'name':"Estimated Cloudbase", 'value':est_cloudbase}))
        af_items.append(add_color({'name':"Metar Cloudbase", 'value':cb}))
        af_items.append(add_color({'name':"Freezing Altitude", 'value':fl}, 4))

        if 'visibility' in metar_d.keys():
            vis = metar_d['visibility'][:-2]
        else:
            vis = ''
        err = ''
        if '/' in vis:
            vis = (int(vis[0]) / int(vis[2]))  # 1/2SM
        elif vis.isnumeric():
            vis = int(vis)
        else:
            vis = 0
        af_items.append(add_color({'name':"Visibility", 'value':vis}))
        
        if 'condition' in metar_d.keys():
            af_items.append(add_color({'name':"Condition", 'value':metar_d['condition']}))
        else:
            af_items.append(add_color({'name':"Condition", 'value':'UNKNOWN'}))
        

    else:
        pa = None
        da = None
        est_cloudbase = None
        err = fe
    #err += ' af: ' + str(af)
    for m in ms:
        m_d = decode_metar(m, ret='dict')
        color = 1
        if m_d['condition'] == 'VFR':
            color = 4
        elif m_d['condition'] == 'MVFR':
            color = 5
        elif m_d['condition'] == 'IFR':
            color = 2
        elif m_d['condition'] == 'LIFR':
            color = 1
        name = "Metar"
        td = get_td(m_d['time'])
        name += " {}:{:02} ago".format(td.seconds//3600, (td.seconds//60)%60)
        af_items.append(add_color({'name':name, 'value':m}, color))

    last_waypoints = waypoint.objects.all().order_by("created_at")[:5]
    context = {'aircraft_rs':aircraft_rs, 'metars':ms, 'xwform':xwform, 'xw':xw,
            'min_alerts':min_alerts, 'metar_l':decode_metar(last_metar), 'gust_factor':gf,
            'pressure_altitude':pa, 'density_altitude':da, 'est_cloudbase': est_cloudbase,
            'night_current':night_current, 'day_current':day_current, 'nc_deadline':nc_deadline,
            'dc_deadline':dc_deadline, 'field_elevation':fe, 'condition':condition, 'err':err,
            'airfield_form':aform, 'gps_form':gps_from_noregex(), 'last_waypoints':last_waypoints,
            'pilot_items':pilot_items, 'airfield':af, 'af_items':af_items, 'next_aform':next_aform}
    return render(request, 'flynote/dashboard.html', context)

@login_required
def show_configs(request):
    user_items = user_config.objects.filter(user=request.user)

    if request.method == 'POST':
        submitted_items = []
        for i in user_items:
            try:
                si = request.POST.get("ui-{}".format(i.id))
                if si != i.value:
                    submitted_items.append({'id':i.id, 'si':si})
            except:
                continue
        for i in submitted_items:
            this_item = user_config.objects.get(pk=i['id'])
            this_item.value = i['si']
            this_item.save()
    user_items = user_config.objects.filter(user=request.user)
    context = {'user_items':user_items, 'title':"{} User Items".format(request.user.username)}
    return render(request, 'flynote/show_configs.html', context)

@login_required
def show_ac_items(request, ptr):
    len_vals = 0
    ac = Aircraft.objects.get(pk=ptr)
    ac_values = Ac_value.objects.filter(ac_item__aircraft=ac)
    len_vals += len(ac_values)
    context = {'ac':ac, 'ac_values':ac_values, 'len_values':len_vals, 'title':"{} Config Items".format(str(ac))}
    return render(request, 'flynote/show_ac_items.html', context)

# @login_required
# def show_mins_item(request, ptr):
#     item = Minimums.objects.get(pk=ptr)
#     form = mins_form(instance=item)
#     context = {'form':form}
#     return render(request, "/", context)

@login_required
def convert_coordinates(request):
    if request.method == 'POST':
        #form = gps_form(request.POST)
        form = gps_from_noregex(request.POST)
        if form.is_valid():
            coords = form.cleaned_data['coords']
            #latrx = '^[0-9]{2}.[0-9]*'
            #latrx = config.objects.get(name='latrx')
            #lonrx = ', .[0-9]{2}.[0-9]*$'
            #lonrx = config.objects.get(name='lonrx')
            #latmatch = re.search(latrx.value, coords)
            #if latmatch:
            #    lat = latmatch.group()
            #else:
            #    lat = ""
            #lonmatch = re.search(lonrx.value, coords)
            #if lonmatch:
            #    lon1 = lonmatch.group()
            #    lon = lon1[1:].strip()
            #else:
            #    lon = ""
            splitstring = str(coords).split(',')
            if len(splitstring) == 2:
                try:
                    lat = float(splitstring[0].strip())
                    lon = float(splitstring[1].strip())
                except:
                    lat = None
                    lon = None
            wp = waypoint(name="noname", lat=lat, lon=lon, input_string=coords, user=request.user)
            wp.save()
    return redirect("dashboard")

@login_required
def update_flight_values(request, ptr):
    aircraft_rs = User_to_aircraft.objects.filter(user=request.user)
    if ptr in [acr.aircraft.id for acr in aircraft_rs]:
        aircraft = Aircraft.objects.get(pk=ptr)
        all_users_utas = User_to_aircraft.objects.filter(aircraft=aircraft)
        uta = aircraft_rs.filter(aircraft=aircraft)[0] #should just be 1
        msg = 'start'
        if request.method == 'POST':
            msg = "{} POST {}".format(msg, request.POST.get('flt-152-tach'))
            logitems = Logitem.objects.filter(uta__in=all_users_utas)
            nonflights = logitems.exclude(logtype="flight")
            flis = Flightlogitem.objects.filter(logitem__uta__in=all_users_utas).order_by('-logitem__date', '-tach')
            show_number = get_log_item_num(request.user)
            if len(flis) > show_number:
                flis = flis[:show_number]
            msg = "{} len-flis {}".format(msg, len(flis))
            for fli in flis:
                getstr = "flt-{}-tach".format(fli.id)
                try:
                    t = request.POST.get(getstr)
                    msg = "{} t {}".format(msg, t)
                    if t:
                        msg = "{} checking {}".format(msg, fli.id)
                        old_t = fli.tach
                        if float(old_t) != float(t):
                            msg = "{} changing to {}".format(msg, t)
                            fli.tach = t
                            fli.save()
                except:
                    msg = "{} continue from {}".format(msg, getstr)
                    continue
        params = urlencode({'msg':msg})
        rev = reverse('show_ac', args=[ptr])
        #url_str = rev + '?' + params
        url_str = rev
        return redirect(url_str)
                

@login_required
def show_waypoint(request, wp_id):
    wp = waypoint.objects.get(pk=wp_id)
    if request.method == 'POST':
        form = waypointForm(request.POST)
        if form.is_valid():
            update_wp = waypoint(id=wp_id, lat=form.cleaned_data['lat'], lon=form.cleaned_data['lon'],
                                    name=form.cleaned_data['name'], user=wp.user, created_at=wp.created_at,
                                    input_string=form.cleaned_data['input_string'], updated_at=datetime.datetime.now())
            update_wp.save()
            wp = update_wp   #not needed. wp is already set correctly
    form = waypointForm(instance=wp)
    #lat_string = get_garmin_string(wp.lat)  #returns list
    lat_strings = get_gps_regex(wp.input_string, 'lat')  #returns list or dicts
    #lon_string = get_garmin_string(wp.lon)
    lon_strings = get_gps_regex(wp.input_string, 'lon')
    #context = {'waypoint':wp, 'form':form, 'lat_string':lat_string, 'lon_string':lon_string}
    context = {'waypoint':wp, 'form':form, 'lat_strings':lat_strings, 'lon_strings':lon_strings}
    return render(request, 'flynote/waypoint.html', context)

@login_required
def show_squawk(request, squawk_id):
    sqk = squawk.objects.get(pk=squawk_id)
    if request.method == 'POST':
        form = squawkform(request.POST)
        if form.is_valid():
            update_sq = squawk(id=squawk_id, name=form.cleaned_data['name'], 
                               description=form.cleaned_data['description'], 
                               aircraft=sqk.aircraft, user=request.user, created_at=sqk.created_at,
                               updated_at=datetime.datetime.now())
            update_sq.save()
            sqk = update_sq
    form = squawkform(instance=sqk)
    context = {'squawk':sqk, 'form':form}
    return render(request, 'flynote/squawk.html', context)


@login_required
def attach_mlog_to_squawk(request, mlog_id):
    mlog = Maintlogitem.objects.get(pk=mlog_id)
    sqform = squawklistform(request.POST)
    if sqform.is_valid():
        sq = sqform.cleaned_data['squawk_item']
        sq.maintenance_log = mlog
        sq.save()
    return redirect('show_maint_item', mlog.id)

@login_required
def show_maint(request, ptr):
    aircraft_rs = User_to_aircraft.objects.filter(user=request.user)
    search_adm = request.GET.get('search_adm','')
    search_note = request.GET.get('search_note','')
    if ptr in [acr.aircraft.id for acr in aircraft_rs]:
        aircraft = Aircraft.objects.get(pk=ptr)
        all_users_utas = User_to_aircraft.objects.filter(aircraft=aircraft)
        logitems = Logitem.objects.filter(uta__in=all_users_utas)
        if search_adm != '':
            adms = Ada_maintitem.objects.filter(note__contains=search_str).order_by("-maintitem__date")
            maint_items = [adm.maintitem for adm in adms]
        elif search_note != '':
            maint_items = Maintlogitem.objects.filter(logitem__in=logitems).filter(logitem__note__contains=search_note).order_by("-date")
        else:
            maint_items = Maintlogitem.objects.filter(logitem__in=logitems).order_by("-date")
        maintform = Maintlogform_v1()
    context = {'maint_items':maint_items, 'ac':aircraft, 'maintform':maintform}
    return render(request, 'flynote/show_maint.html', context)

@login_required
def show_maint_item(request, ptr):

    mli = Maintlogitem.objects.get(pk=ptr)
    if request.method == 'POST':
        form = Maintlogform(request.POST)
        if form.is_valid():
            mli = form.save()
    ada_mlis = Ada_maintitem.objects.filter(maintitem=mli)
    add_ad_form = ad_quickpick()
    ta_form = tach_adjust_form()
    squawklist = squawklistform()
    resolved_squawks = squawk.objects.filter(maintenance_log=mli)
    context = {'maint_item':mli, 'ADs':ada_mlis, 'add_ad_form':add_ad_form, 
            'file_form':UploadFileForm(), 'files':Maintitem_file.objects.filter(maintitem=mli),
                'tach_adjust_form':ta_form, 'squawklist':squawklist, 'resolved_squawks':resolved_squawks,
                'maintform':Maintlogform(instance=mli)}
    return render(request, 'flynote/show_maint_item.html', context)

@login_required
def new_ada(request, ptr):
    mli = Maintlogitem.objects.get(pk=ptr)
    assert request.method == 'POST', "Should be POST"
    form = ad_quickpick(request.POST)
    if form.is_valid():
        ada = form.cleaned_data['ada']
        adm = Ada_maintitem(maintitem=mli, ada=ada, note="Added to Maint log")
        adm.save()
    return redirect('show_maint_item', ptr)

@login_required
def create_ttaf_adjust(request, ptr): #maintitem pointer
    maintitem = Maintlogitem.objects.get(pk=ptr)
    if request.method == 'POST':
        form = tach_adjust_form(request.POST)
        if form.is_valid():
            hours = form.cleaned_data['hours']
            ta = Tach_adjust(hours=hours, category="airframe", firstlog=maintitem)
            ta.save()

    return redirect('show_maint_item', ptr)

@login_required
def show_ada_mli(request, ptr):
    ada_mli = Ada_maintitem.objects.get(pk=ptr)
    if request.method == 'POST':
        form = Ada_maint_form(request.POST)
        if form.is_valid():
            ada_mli.note = form.cleaned_data['note']
            ada_mli.save()
    context = {'ada_mli':ada_mli, 'form':Ada_maint_form(instance=ada_mli)}
    return render(request, 'flynote/show_ada_mli.html', context)

@login_required
def add_maint(request, ptr):
    aircraft_rs = User_to_aircraft.objects.filter(user=request.user)
    if ptr in [acr.aircraft.id for acr in aircraft_rs]:
        aircraft = Aircraft.objects.get(pk=ptr)
        for uta in aircraft_rs:
            if uta.aircraft == aircraft:
                this_uta = uta
                break

        if request.method == 'POST':
            form = Maintlogform_v1(request.POST)
            if form.is_valid():
                cd = form.cleaned_data
                date = cd['date']
                note = cd['note']
                tach = cd['tach']
                oc = cd['oil_changed']
                af = cd['annual_finished']
                txpndr = cd['transponder_certified']
                li = Logitem(date=date, note=note, uta=this_uta)
                li.save()
                mli = Maintlogitem(tach=tach, oil_changed=oc, annual_finished=af, logitem=li, 
                                   transponder_certified=txpndr, date=date)
                mli.save()
    return redirect('show_maint', ptr)

@login_required
def delete_squawk(request, sq_ptr):   #ptr is for aircraft
    sq = squawk.objects.get(pk=sq_ptr)
    aircraft_rs = User_to_aircraft.objects.filter(user=request.user)
    if sq.aircraft.id in [acr.aircraft.id for acr in aircraft_rs]:
        aircraft = sq.aircraft
        for uta in aircraft_rs:
            if uta.aircraft == aircraft:
                this_uta = uta
                break
    li = Logitem(date=datetime.date.today(), note="Deleted Squawk %d" % sq_ptr, uta=this_uta)
    li.save()
    mli = Maintlogitem(tach=get_latest_tach(sq.aircraft)[0], oil_changed=False, annual_finished=False, logitem=li, date=li.date)
    mli.save()
    sq = squawk.objects.get(pk=sq_ptr)
    sq.maintenance_log = mli
    sq.save()
    return redirect('show_ac', sq.aircraft.id)


@login_required
def add_file_maint_item(request, ptr):
    maintitem = Maintlogitem.objects.get(pk=ptr)
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            f = request.FILES['file']
            n = form.cleaned_data['title']
            if n != '':
                fname = n
            else:
                fname = f.name
            file_id = file_upload(f, name=fname)
            file_object = File.objects.get(pk=file_id)
            mif = Maintitem_file(file=file_object, maintitem=maintitem)
            mif.save()
    return redirect('show_maint_item', ptr)

@login_required
def get_file(request, ptr):
    try:
        file_object = File.objects.get(pk=ptr)
    except Exception as e:
        return None
    path = get_path(file_object)

    try:
        file_sys_object = open(path, 'rb')
    except Exception as e:
        #log exception
        return redirect('file_not_found', ptr)

    try:
        file_response = FileResponse(file_sys_object, filename=file_object.name, as_attachment=True)
    except Exception as e:
        #log exception
        return None

    return file_response


@login_required
def show_flights(request, ptr):
    aircraft_rs = User_to_aircraft.objects.filter(user=request.user)
    if ptr in [acr.aircraft.id for acr in aircraft_rs]:
        aircraft = Aircraft.objects.get(pk=ptr)
        all_users_utas = User_to_aircraft.objects.filter(aircraft=aircraft)
        flis = Flightlogitem.objects.filter(logitem__uta__in=all_users_utas).order_by('-logitem__date')
        flights = []
        last_tach = 0.0
        for fli in flis:
            if fli.fuel != None:
                if fli.fuel == "not entered":
                    gph = '0'
                elif float(fli.fuel) == 0:
                    gph = '0'
                else:
                    gph = str(round(float(fli.fuel)/float(fli.hours),1))
            if fli.tach != None:
                if float(fli.tach) > last_tach:
                    last_tach = float(fli.tach)
            flights.append({'li':fli.logitem, 'fli':fli, 'gph':gph})
        context = {'ac':aircraft, 'flights':flights, 'title':"{} Flights".format(request.user)}
        return render(request, 'flynote/show_flights.html', context)

@login_required
def show_ac(request, ptr):

    aircraft_rs = User_to_aircraft.objects.filter(user=request.user)
    if ptr in [acr.aircraft.id for acr in aircraft_rs]:
        aircraft = Aircraft.objects.get(pk=ptr)
        uta = aircraft_rs.filter(aircraft=aircraft)[0] #should just be 1
        all_users_utas = User_to_aircraft.objects.filter(aircraft=aircraft)
        if request.method == "POST":  #received flight log
            form = Flightlog(request.POST)
            if form.is_valid():
                note = form.cleaned_data['note']
                date = form.cleaned_data['date']
                tach = form.cleaned_data['tach']
                hours = form.cleaned_data['hours']
                night_landings = form.cleaned_data['night_landings']
                day_landings = form.cleaned_data['day_landings']
                fu = form.cleaned_data['fuel']
                if night_landings == None:
                    night_landings = 0
                f = float(tach)
                h = float(hours)
                if fu != None:
                    fu = float(fu)
                else:
                    fu = "not entered"
                li = Logitem(uta=uta, logtype="flight", note=note, date=date)
                li.save()
                fl = Flightlogitem(note=note, tach=str(f), hours=str(h), fuel=str(fu),
                                   logitem=li, night_landings=night_landings, day_landings=day_landings)
                fl.save()
        logitems = Logitem.objects.filter(uta__in=all_users_utas)
        nonflights = logitems.exclude(logtype="flight")
        flis = Flightlogitem.objects.filter(logitem__uta__in=all_users_utas).order_by('-logitem__date', '-tach')
        lenflis = len(flis)
        show_number = get_log_item_num(request.user)
        if lenflis > show_number:
            flis = flis[:show_number]
            snipped_flis = lenflis - show_number
        
        ac_items = []

        ttaf = get_latest_ttaf(aircraft)
        flights = []
        last_tach = 0.0
        for fli in flis:
            if fli.fuel != None:
                if fli.fuel == "not entered":
                    gph = '0'
                elif float(fli.fuel) == 0:
                    gph = '0'
                else:
                    gph = str(round(float(fli.fuel)/float(fli.hours),1))
            else:
                gph = '0'
            if fli.tach != None:
                if float(fli.tach) > last_tach:
                    last_tach = float(fli.tach)
            flights.append({'li':fli.logitem, 'fli':fli, 'gph':gph})
        ac_items.append(add_color({'name':"Last Tach", 'value':last_tach}))
        ac_items.append(add_color({'name':"Total Time Engine", 'value':get_TTE(aircraft)}))
        ac_items.append(add_color({'name':"Total Time Airframe", 'value':round(ttaf, 1)}))
        maint_items = Maintlogitem.objects.filter(logitem__in=logitems)
        last_oil = 0.0
        last_annual = datetime.date(1900, 1, 1) 
        last_txpndr = datetime.date(1900, 1, 1)
        last_pitot = datetime.date(1900, 1, 1)
        last_pitot_id = -1
        last_annual_id = -1
        last_txpndr_id = -1
        for mi in maint_items:
            if mi.oil_changed:
                this_ttaf = get_latest_ttaf(aircraft, mi.logitem.date)
                if float(this_ttaf) > last_oil:
                    last_oil = float(mi.tach)
            if mi.transponder_certified:
                if mi.date > last_txpndr:
                    last_txpndr = mi.date
                    last_txpndr_id = mi.id
            if mi.annual_finished:
                if mi.date > last_annual:
                    last_annual = mi.date
                    last_annual_id = mi.id
            if mi.pitot_static_certified:
                if mi.date > last_pitot:
                    last_pitot = mi.date
                    last_pitot_id = mi.id
        oil_frequency = int(get_or_put_one_ac_item(aircraft, "oil frequency", 25))
        oil_due = last_oil + oil_frequency
        ac_items.append(add_color({'name':"Oil Due (every {} hrs)".format(oil_frequency), 'value':oil_due}))

        hours_remaining = round(oil_due - last_tach, 1)
        c = get_oil_color(hours_remaining, request.user)
        ac_items.append(add_color({'name':"Oil change hours remaining", 'value':hours_remaining}, c))

        annual_due = datetime.date(last_annual.year + 1, last_annual.month + 1, 1)
        days_remaining = (annual_due - datetime.date.today()).days
        ac_items.append(add_color({'name':"Annual Due", 'value':annual_due, 'mi_id':last_annual_id}))
        ac_items.append(add_color({'name':"Days Remaining before annual", 'value':days_remaining}))

        txpndr_due = datetime.date(last_txpndr.year + 2, last_txpndr.month + 1, 1)
        days_remaining = (txpndr_due - datetime.date.today()).days
        txpndr_warning = int(get_or_put_one_ac_item(aircraft, "txpndr_warn", 30))
        txpndr_color = 3
        if days_remaining < txpndr_warning:
            txpndr_color = 2
        if days_remaining < 0:
            txpndr_color = 1
        ac_items.append(add_color({'name':"Transponder Cert Due", 'value':txpndr_due, 'mi_id':last_txpndr_id}, txpndr_color))
        ac_items.append(add_color({'name':"Days Remaining before Transponder Due", 'value':days_remaining}, txpndr_color))

        pitot_due = datetime.date(last_pitot.year + 2, last_pitot.month + 1, 1)
        days_remaining = (pitot_due - datetime.date.today()).days
        pitot_warning = int(get_or_put_one_ac_item(aircraft, "pitot_warn", 30))
        pitot_color = 3
        if days_remaining < pitot_warning:
            pitot_color = 2
        if days_remaining < 0:
            pitot_color = 1
        ac_items.append(add_color({'name':"Pitot/Static Cert Due", 'value':pitot_due, 'mi_id':last_pitot_id}, pitot_color))
        ac_items.append(add_color({'name':"Days remaining before Pitot/Static Due", 'value':days_remaining}, pitot_color))
        
        tach_log = get_tach_log(aircraft,request.GET.get('days_back',30))
        days_back = len(tach_log)
        ADs = AD_aircraft.objects.filter(aircraft=aircraft).order_by('ad__number')
        AD_warnings = []
        for ad in ADs:
            if ad.warning:
                AD_warnings.append(ad)
        AD_warning = len(AD_warnings) > 0
    else:
        aircraft = None
        return redirect("dashboard")
    squawks = squawk.objects.filter(aircraft=aircraft).filter(maintenance_log=None)
    quick_squawk_form = quicksquawk()
    form = Flightlog()
    ac_ptr = "{}_{}".format(aircraft.name, aircraft.id)
    u_ptr = "{}_{}".format(request.user, request.user.id)
    form.fields['tach'].help_text = "Last Tach: {}".format(last_tach)
    context = {'ac':aircraft, 'logitems':logitems, 'flights':flights, 'ptr':ptr,
               'nonflights':nonflights, 'form':form,
               'oil_due':oil_due, 'hours_remaining':hours_remaining,'last_annual':last_annual,
               'days_remaining':days_remaining, 'wandb':get_wandb(ptr), 'tach_log':tach_log,
               'days_back':days_back, 'TTE':get_TTE(aircraft), 'ADs':ADs, 'snipped_flis':snipped_flis, 
               'ttaf':round(ttaf, 1), 'squawks':squawks, 'quick_squawk_form':quick_squawk_form, 
               'AD_warning':AD_warning, 'AD_warnings':AD_warnings, 'ac_items':ac_items, 'title':aircraft.name,
               'msg':request.GET.get('msg'), 'last_tach':last_tach, 'ac_ptr':ac_ptr, 'u_ptr':u_ptr,}
    return render(request, 'flynote/aircraft.html', context)

def squawk_quick_add(request, aircraft_id):
    if request.method == 'POST':
        aircraft = Aircraft.objects.get(pk=aircraft_id)
        form = quicksquawk(request.POST)
        if form.is_valid():
            sq = squawk(name=form.cleaned_data['name'], description='quick entry', aircraft=aircraft)
            sq.save()

    return redirect('show_ac', aircraft_id)

def add_ad(request):
    if request.method == 'POST':
        form = Ad_form(request.POST)
        if form.is_valid():
            desc = form.cleaned_data['description']
            num = form.cleaned_data['number']
            sb = form.cleaned_data['superseded_by']
            ad = AD(description=desc, number=num, superseded_by=sb)
            ad.save()
    else:
        pass
    context = {'form':Ad_form()}
    return render(request, 'flynote/ad.html', context)

@login_required
def show_ads(request, ptr):
    aircraft_rs = User_to_aircraft.objects.filter(user=request.user)
    if ptr in [acr.aircraft.id for acr in aircraft_rs]:
        aircraft = Aircraft.objects.get(pk=ptr)
    else:
        return redirect('dash')
    ttaf = get_latest_ttaf(aircraft)
    glt = get_latest_tach(aircraft)
    last_tach = glt[0]
    ad_acs = AD_aircraft.objects.filter(aircraft=aircraft).order_by("complied", "ad__number")
    ads = []
    show_nons = get_or_create_user_item('Show N/A ADs', 1, request.user)
    if show_nons:
        pass
    else:
        ad_acs = ad_acs.filter(applicable=True).order_by("complied", "-recurring", "ad__number")
    for ad in ad_acs:
        ad_dict = {'ad_ac':ad}
        if not ad.applicable:
            ad_dict['level'] = 'dark'
        else:
            level = 0
            if ad.due_tach != None:
                rem = ad.due_tach - float(last_tach)
                if rem < 20: #make configurable?
                    level = 2
                    ad.warning = True
                if rem < 0:
                    level += 10
                    ad.warning = True
            if ad.due_date != None:
                td = ad.due_date - datetime.date.today()
                days = td.days
                if days < 0:
                    level += 10
                    ad.warning = True
                elif days < 100:
                    level += 2
                    ad.warning = True
            if level > 0:
                ad.save()
            if not ad.complied:
                level += 100
            if level >= 10:
                ad_dict['level'] = 'danger'
            elif level >= 2:
                ad_dict['level'] = 'warning'
            elif ad.recurring:
                ad_dict['level'] = 'primary'
            else:
                ad_dict['level'] = 'success'
        ads.append(ad_dict)
    unused_ADs = AD.objects.exclude(id__in=[ad_ac.ad.id for ad_ac in ad_acs])
    context = {'ac':aircraft, 'ads':ads, 'unused_ADs':unused_ADs, 'last_tach': last_tach,
                'show_nons':show_nons}
    return render(request, 'flynote/show_ads.html', context)

@login_required
def add_ad_to_ac(request, ad_ptr, ac_ptr):
    aircraft_rs = User_to_aircraft.objects.filter(user=request.user)
    if ac_ptr in [acr.aircraft.id for acr in aircraft_rs]:
        aircraft = Aircraft.objects.get(pk=ac_ptr)
    else:
        return redirect('dash')
    ad = AD.objects.get(pk=ad_ptr)
    ac = Aircraft.objects.get(pk=ac_ptr)
    adac = AD_aircraft(ad=ad, aircraft=ac, note="Added to %s" % ac.name, applicable=True)
    adac.save()
    return redirect('show_ads', ac.id)

@login_required
def change_na_ads(request, show_nons, ptr_ac):
    current_value = get_or_create_user_item('Show N/A ADs', 1, request.user)
    i = user_config.objects.filter(user=request.user).filter(name='Show N/A ADs')
    if len(i) == 1:
        i[0].value = str(show_nons)
        i[0].save()
    return redirect('show_ads', ptr_ac)


@login_required
def show_ad_ac(request, ptr):
    ad_ac = AD_aircraft.objects.get(pk=ptr)
    if request.method == 'POST':
        form = ad_aircraft_mform(request.POST, instance=ad_ac)
        if form.is_valid():
            form.save()
    else:
        form = ad_aircraft_mform(instance=ad_ac)
    ad_form = ad_mform(instance=ad_ac.ad)
    mli_links = Ada_maintitem.objects.filter(ada=ad_ac).order_by('maintitem__logitem__date')
    maint_items = []
    for mli in mli_links:
        maint_items.append({'mli':mli, 'ttaf':get_latest_ttaf(ad_ac.aircraft, mli.maintitem.date)})
    context = {'form':form, 'ad_ac':ad_ac, 'ad_form':ad_form, 'maintitem_links':maint_items}
    return render(request, 'flynote/show_ad_ac.html', context)

def update_ad(request, ad_ptr, ad_ac_ptr):
    ad = AD.objects.get(pk=ad_ptr)
    if request.method == 'POST':
        form = ad_mform(request.POST, instance=ad)
        if form.is_valid():
            form.save()
    return redirect('show_ad_ac', ad_ac_ptr)

def add_wandb_image(request, ptr):
    ac = Aircraft.objects.get(pk=ptr)
    if request.method == 'POST':
        wbf_cat = Ac_category.objects.filter(name='wandb_image')
        if len(wbf_cat) < 1:
            wbf_cat = Ac_category(name="wandb_image")
            wbf_cat.save()
        else:
            wbf_cat = wbf_cat[0]
        wbi = Ac_item.objects.filter(aircraft=ac, category=wbf_cat)
        if len(wbi) < 1:
            wbi = Ac_item(aircraft=ac, category=wbf_cat)
            wbi.save()
        else:
            wbi = wbi[0]
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            f = request.FILES['file']
            n = form.cleaned_data['title']
            if n != '':
                fname = n
            else:
                fname = f.name
            file_id = file_upload(f, name=fname)
            file_object = File.objects.get(pk=file_id)
            wbf = Ac_file(file=file_object, ac_item=wbi)
            wbf.save()
    return redirect('wandb', ptr)

def update_wandb(request, ptr):
    ac = Aircraft.objects.get(pk=ptr)
    if request.method == 'POST':
        updated_weights = []
        wb_items = wandb_item.objects.filter(category__aircraft=ac)
        for wb_item in wb_items:
            try:
                w = request.POST.get("wbi-{}-weight".format(wb_item.id))
                if w:
                    updated_weights.append({'id':wb_item.id, 'weight':w})
            except:
                continue
        for updated_weight in updated_weights:
            wbi = wandb_item.objects.get(pk=updated_weight['id'])
            changed = False
            w = int(updated_weight['weight'])
            if w != wbi.weight:
                wbi.weight = w
                changed = True
            if changed:
                wbi.save()
    return redirect('wandb', ptr)

def add_ad_ac(request):
    #AD_aircraft
    if request.method == 'POST':
        form = ad_aircraft_form(request.POST)
        if form.is_valid():
            ad = form.cleaned_data['ad']
            ac = form.cleaned_data['aircraft']
            due_tach = form.cleaned_data['due_tach']
            due_date = form.cleaned_data['due_date']
            complied = form.cleaned_data['complied']
            ap = form.cleaned_data['applicable']
            if complied == None:
                complied = False
            cli = form.cleaned_data['compliance_log_item']
            recurring = form.cleaned_data['recurring']
            if recurring == None:
                recurring = False
            if ap == None:
                ap = False
            ad_ac = AD_aircraft(ad=ad, aircraft=ac, due_tach=due_tach, due_date=due_date, complied=complied, compliance_log_item=cli, recurring=recurring, applicable=ap)
            ad_ac.save()
    else:
        pass
    context = {'form':ad_aircraft_form()}
    return render(request, 'flynote/ad_ac.html', context)

def show_fl(request, ptr):
    fl = Flightlogitem.objects.get(pk=ptr)
    if request.method == "POST":
        form = Flightlog(request.POST)
        if form.is_valid():
            date = form.cleaned_data['date']
            note = form.cleaned_data['note']
            tach = form.cleaned_data['tach']
            hours = form.cleaned_data['hours']
            fuel = form.cleaned_data['fuel']
            day_landings = form.cleaned_data['day_landings']
            night_landings = form.cleaned_data['night_landings']
            if night_landings == None:
                night_landings = 0
            fl.logitem.date = date
            fl.logitem.save()
            fl.note = note
            fl.tach = tach
            fl.hours = hours
            fl.fuel = fuel
            fl.night_landings = night_landings
            fl.day_landings = day_landings
            fl.save()
            
    else:
        pass
    initial = {'date':fl.logitem.date, 'note':fl.note, 'tach':fl.tach, 'hours':fl.hours, 'fuel':fl.fuel, 'night_landings':fl.night_landings, 'day_landings':fl.day_landings}
    form = Flightlog(initial=initial)
    context = {"flightlogitem":fl, "form":form}
    return render(request, "flynote/show_fl.html", context)

def wandb(request, ptr):
    ac = Aircraft.objects.get(pk=ptr)
    wb_categories = wandb_category.objects.filter(aircraft=ac)
    wandb = []
    ac_moment = 0
    ac_weight = 0
    for wbc in wb_categories:
        wb_items = wandb_item.objects.filter(category=wbc)
        total_moment = 0
        cat_weight = 0
        for wb_item in wb_items:
            total_moment += wb_item.moment()
            cat_weight += wb_item.weight
        ac_moment += total_moment
        ac_weight += cat_weight
        if ac_weight != 0:
            ac_arm = round(ac_moment/ac_weight, 2)
        else:
            ac_arm = 0
        wandb.append({'wb_category':wbc, 'wb_items':wb_items, 'total_moment':round(total_moment, 2)})
    gross_weight = get_gross_weight(ptr)
    max_aft_cg = get_max_aft_cg(ptr)
    cg_range = get_cg_range(ptr, ac_weight)
    if ac_arm < cg_range[0] or ac_arm > cg_range[1]:
        out_of_range = True
    else:
        out_of_range = False
    wbf = Ac_file.objects.filter(ac_item__category__name='wandb_image', ac_item__aircraft=ac)
    wbf_count = len(wbf)
    if wbf_count < 1:
        wbf_image = None
    else:
        wbf_image = wbf.last()
    context = {'ac':ac, 'wandb':wandb, 'ac_moment':round(ac_moment, 2), 'ac_weight':ac_weight, 
            'ac_arm':ac_arm, 'gross_weight':gross_weight.value, 'max_aft_cg':max_aft_cg.value,
            'wbf_form':UploadFileForm(), 'wbf_count':wbf_count, 'wbf_image':wbf_image,
            'min_cg':cg_range[0], 'max_cg':cg_range[1], 'out_of_range':out_of_range}
    return render(request, 'flynote/wandb.html', context)

def login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    n = request.GET.get('next', '/flynote/dash')
    if request.method == 'POST':
        lform = LoginForm(request.POST)
        if lform.is_valid():
            username = lform.cleaned_data['username']
            pw = lform.cleaned_data['password']
            user = authenticate(request, username=username, password=pw)
            if user is not None:
                djlogin(request, user)
                return redirect(n)
            else:
                return redirect('login')
    else:
        lform = LoginForm()
    context = {
            'form':lform,
            'next_page':n,
            }
    return render(request, 'flynote/login.html', context)

def add_fast_log(request, ac_ptr, u_ptr):
    ac_list = ac_ptr.split('_')
    u_list = u_ptr.split('_')
    ac_pk = int(ac_list[1])
    ac_name = ac_list[0]
    u_pk = int(u_list[1])
    u_name = u_list[0]
    ac = Aircraft.objects.get(pk=ac_pk)
    error = False
    msg = ""
    if ac.name != ac_name:
        error = True
    u = User.objects.get(pk=u_pk)
    dir_u = dir(u)
    if u.username != u_name:
        error = True
    uta = User_to_aircraft.objects.get(aircraft=ac, user=u)
    if uta == None:
        error = True
        msg += "UTA "
    if error:
        msg += "Invalid"
        params = urlencode({'msg':msg})
        rev = reverse('show_ac', args=[ac_pk])
        url_str = rev + '?' + params
        return redirect(url_str)
    if request.method == 'POST':
        form = Fastlog(request.POST)
        if form.is_valid():
            if form.cleaned_data['note'] is not None:
                form_note = "Fastflight: " + form.cleaned_data['note'] 
            else:
                form_note = "Fast Flight entry"
            if form.cleaned_data['tach'] is not None:
                form_tach = form.cleaned_data['tach']
            else:
                last_tach_tp = get_latest_tach(ac)  #tuple (last_tach_char, last_date)
                last_tach = float(last_tach_tp[0]) + 0.5
                form_tach = str(last_tach)
            if form.cleaned_data['date'] is not None:
                #form_date = form.fields['date']
                form_date = datetime.date.today()
            else:
                form_date = datetime.date.today()
            day_landings = 1
            night_landings = 0
            hours = "0.1"
            li = Logitem(uta=uta, logtype="flight", note="Fast Flight Form", date=form_date)
            li.save()
            fl = Flightlogitem(note=form_note, tach=form_tach, hours=hours, fuel="not entered", logitem=li, 
                               night_landings=night_landings, day_landings=day_landings)
            fl.save()
            context = {"hours":hours, "date":li.date, "note":form_note, "tach":form_tach, "msg":msg, "form":Fastlog(),
                       "ac":ac, "u":u, "ac_ptr":ac_ptr, "u_ptr":u_ptr}
            return render(request, 'flynote/fast_flight.html', context)

    else:
        form = Fastlog()
        context = {'form':form, "ac":ac, "u":u, "ac_ptr":ac_ptr, "u_ptr":u_ptr }
        return render(request, 'flynote/fast_flight.html', context)