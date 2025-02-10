from django.shortcuts import render, redirect
from django.http import HttpResponse, FileResponse
from .models import (Aircraft, User_to_aircraft, Logitem, Flightlogitem, Maintlogitem,
                    Airfield, Airfield_to_uta, wandb_category, wandb_item, Ac_item, 
                    AD, AD_aircraft, Ada_maintitem, File, Maintitem_file, Tach_adjust,
                    Ac_file, Ac_category, Minimums, Runway, waypoint, config, squawk )
from django.contrib.auth import authenticate
from django.contrib.auth import login as djlogin
from django.contrib.auth import logout as djlogout
from django.contrib.auth.decorators import login_required
from .forms import (Quicklog, Flightlog, Ad_form, ad_aircraft_form, 
                   ad_aircraft_mform, ad_mform, Maintlogform, ad_quickpick,
                   Ada_maint_form, UploadFileForm, tach_adjust_form, Crosswind_form,
                   LoginForm, Airfield_form, gps_form, waypointForm, gps_from_noregex,
                   quicksquawk, squawkform, squawklistform)
import datetime
import json, re
from .helper import ( get_metars, get_wandb, get_gross_weight, get_max_aft_cg, 
        get_tach_log, get_TTE, file_upload, get_path, get_latest_ttaf, get_cg_range,
        get_latest_tach, get_crosswind, decode_metar, get_angle_difference, get_pressure_alt,
        get_density_alt, get_cloudbase, get_dewpoint_int, get_landings, get_currency_deadline,
        get_field_elevation, get_garmin_string, get_gps_regex)

# Create your views here.
#comment test


def home(request):
    return HttpResponse("Hello flynote")

@login_required
def dash(request):
    aircraft_rs = User_to_aircraft.objects.filter(user=request.user)
    airfield_to_utas = Airfield_to_uta.objects.filter(uta__in=aircraft_rs)
    metars = []
    mins = Minimums.objects.filter(user=request.user)
    if len(mins) == 0:
        mins = None
    else:
        mins = mins[0]
    get_airfield = request.GET.get('airfield', None)    
    last_metar = None
    last_airfield = None
    for aftu in airfield_to_utas:
        #k_id = aftu.airfield.k_id
        #ms = get_metars(k_id, hours=4)
        #metars.append({'k_id':k_id, 'metar_list':ms})
        #last_metar = ms[0]
        last_airfield = aftu.airfield

    if get_airfield == None:
        if last_airfield == None:
            af = 'KCEU'
        else:
            af = last_airfield.k_id
        ms = get_metars(af, hours=4)
        metars.append({'k_id':af, 'metar_list':ms})
        metar_d = decode_metar(ms[0], ret='dict')
    else:
        af = get_airfield
        ms = get_metars(af, hours=4)
        metars.append({'k_id':af, 'metar_list':ms})
        metar_d = decode_metar(ms[0], ret='dict')
    last_metar = ms[0]
    xwform = Crosswind_form()
    xw = None
    aform = Airfield_form(initial={'airfield':af})

    #currency
    nl = get_landings(request.user, 90, 'night')
    dl = get_landings(request.user, 90, 'day')
    night_current =  (nl >= 3)
    day_current = (dl >= 3)
    if night_current:
        nc_deadline = get_currency_deadline(request.user, 'night')
    else:
        nc_deadline = None
    if day_current:
        dc_deadline = get_currency_deadline(request.user, 'day')
    else:
        dc_deadline = None
    
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
    if int(xw['speed']) > mins.crosswind:
        min_alerts['crosswind'] = True
    if 'gusts' in metar_d.keys():
        if int(metar_d['gusts']) >= mins.wind:
            min_alerts['wind'] = True
        gf = int(metar_d['gusts']) - int(metar_d['wind_speed'])
    #fe = int(last_airfield.field_elevation)
    fe = get_field_elevation(af)
    dp = get_dewpoint_int(metar_d['dewpoint'])
    condition = "UNKNOWN"
    if isinstance(fe, int):
        pa = get_pressure_alt(fe, metar_d['altimeter'][1:])
        da = get_density_alt(pa, metar_d['temp'])
        est_cloudbase = get_cloudbase(metar_d['temp'], dp) + fe
        cb = metar_d['lowest_ceiling']
        vis = metar_d['visibility'][:-2]
        err = ''
        if '/' in vis:
            vis = (int(vis[0]) / int(vis[2]))  # 1/2SM
        else:
            vis = int(vis)
        if cb > 3000 and vis > 5:
            condition = 'VFR'
        elif cb >= 1000 and vis >= 3:
            condition = 'MVFR'
        elif cb >= 500 and vis >= 1:
            condition = 'IFR'
        elif cb < 500 or vis < 1:
            condition = 'LIFR'
        else:
            condition = "UNKNOWN"
    else:
        pa = None
        da = None
        est_cloudbase = None
        err = fe
    err += ' af: ' + str(af)
    last_waypoints = waypoint.objects.all().order_by("created_at")[:5]
    context = {'aircraft_rs':aircraft_rs, 'metars':metars, 'xwform':xwform, 'xw':xw,
            'min_alerts':min_alerts, 'metar_l':decode_metar(last_metar), 'gust_factor':gf,
            'pressure_altitude':pa, 'density_altitude':da, 'est_cloudbase': est_cloudbase,
            'night_current':night_current, 'day_current':day_current, 'nc_deadline':nc_deadline,
            'dc_deadline':dc_deadline, 'field_elevation':fe, 'condition':condition, 'err':err,
            'airfield_form':aform, 'gps_form':gps_from_noregex(), 'last_waypoints':last_waypoints}
    return render(request, 'flynote/dashboard.html', context)

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
        maintform = Maintlogform()
    context = {'maint_items':maint_items, 'ac':aircraft, 'maintform':maintform}
    return render(request, 'flynote/show_maint.html', context)

@login_required
def show_maint_item(request, ptr):

    mli = Maintlogitem.objects.get(pk=ptr)
    if request.method == 'POST':
        form = ad_quickpick(request.POST)
        if form.is_valid():
            ada = form.cleaned_data['ada']
            adm = Ada_maintitem(maintitem=mli, ada=ada, note="Added to Maint log")
            adm.save()
    ada_mlis = Ada_maintitem.objects.filter(maintitem=mli)
    add_ad_form = ad_quickpick()
    ta_form = tach_adjust_form()
    squawklist = squawklistform()
    resolved_squawks = squawk.objects.filter(maintenance_log=mli)
    context = {'maint_item':mli, 'ADs':ada_mlis, 'add_ad_form':add_ad_form, 
            'file_form':UploadFileForm(), 'files':Maintitem_file.objects.filter(maintitem=mli),
                'tach_adjust_form':ta_form, 'squawklist':squawklist, 'resolved_squawks':resolved_squawks}
    return render(request, 'flynote/show_maint_item.html', context)

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
            form = Maintlogform(request.POST)
            if form.is_valid():
                cd = form.cleaned_data
                date = cd['date']
                note = cd['note']
                tach = cd['tach']
                oc = cd['oil_changed']
                af = cd['annual_finished']
                li = Logitem(date=date, note=note, uta=this_uta)
                li.save()
                mli = Maintlogitem(tach=tach, oil_changed=oc, annual_finished=af, logitem=li, date=date)
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
    li = Logitem(date=datetime.today(), note="Deleted Squawk %d" % sq_ptr, uta=this_uta)
    li.save()
    mli = Maintlogitem(tach=get_latest_tach, oil_changed=False, annual_finished=False, logitem=li, date=li.date)
    mli.save()
    sq = squawk_item.objects.get(pk=sq_ptr)
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
        context = {'ac':aircraft, 'flights':flights,}
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
        show_number = 7
        if lenflis > show_number:
            flis = flis[:show_number]
            snipped_flis = lenflis - show_number
            
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
        maint_items = Maintlogitem.objects.filter(logitem__in=logitems)
        last_oil = 0.0
        last_annual = datetime.date(1900, 1, 1) 
        for mi in maint_items:
            if mi.oil_changed:
                #if float(mi.tach) > last_oil:
                this_ttaf = get_latest_ttaf(aircraft, mi.logitem.date)
                if float(this_ttaf) > last_oil:
                    last_oil = float(mi.tach)
            if mi.annual_finished:
                if mi.date > last_annual:
                    last_annual = mi.date
        oil_due = last_oil + 50
        hours_remaining = round(oil_due - last_tach, 1)
        #annual_due = datetime.date(last_annual.year + 1, last_annual.month, last_annual.day)
        annual_due = datetime.date(last_annual.year + 1, last_annual.month + 1, 1)
        days_remaining = (annual_due - datetime.date.today()).days
        tach_log = get_tach_log(aircraft,request.GET.get('days_back',30))
        days_back = len(tach_log)
        ADs = AD_aircraft.objects.filter(aircraft=aircraft).order_by('ad__number')
        ttaf = get_latest_ttaf(aircraft)
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
    context = {'ac':aircraft, 'logitems':logitems, 'flights':flights, 'ptr':ptr,
               'nonflights':nonflights, 'form':Flightlog(),
               'oil_due':oil_due, 'hours_remaining':hours_remaining,'last_annual':last_annual,
               'days_remaining':days_remaining, 'wandb':get_wandb(ptr), 'tach_log':tach_log,
               'days_back':days_back, 'TTE':get_TTE(aircraft), 'ADs':ADs, 'snipped_flis':lenflis, 
               'ttaf':ttaf, 'squawks':squawks, 'quick_squawk_form':quick_squawk_form, 
               'AD_warning':AD_warning, 'AD_warnings':AD_warnings}
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
    ad_acs = AD_aircraft.objects.filter(aircraft=aircraft).order_by("ad__number")
    ads = []
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
                td = ad.due_date - date.today()
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
    context = {'ac':aircraft, 'ads':ads, 'unused_ADs':unused_ADs, 'last_tach': last_tach}
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
