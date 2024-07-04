import json
from urllib import request
from .models import ( Aircraft, wandb_item, wandb_category, Ac_item, Ac_value, Flightlogitem,
                    File, Tach_adjust, Maintlogitem, wandb_box_segment )
from datetime import date, timedelta
from django.db.models import Sum
from django.core.files.storage import default_storage
from django.conf import settings
import os, math

metar_url = "https://aviationweather.gov/cgi-bin/data/metar.php"
fe_url = "https://aviationweather.gov/api/data/airport"

#?ids=KMCI&format=json&taf=false&hours=8"

def get_metars(k_id, hours=1):
    if len(k_id) == 4:
        pass
    elif len(k_id) == 3:
        k_id = 'k' + k_id
    else:
        return None
    resp = request.urlopen(metar_url + '?ids=' + k_id + '&format=json&taf=false&hours=' + str(hours))
    j = json.load(resp)
    resplist = []
    for i in j:
        resplist.append(i['rawOb'])
    return resplist

def get_field_elevation(k_id):
    if len(k_id) == 4:
        pass
    elif len(k_id) == 3:
        k_id = 'k' + k_id
    else:
        return None
    k_id = k_id.upper()
    req_url = fe_url + '?ids=' + k_id + '&format=json'
    resp = request.urlopen(req_url)
    j = json.load(resp)
    resp.close()
    resplist = []
    for i in j:
        resplist.append(i['elev'])
    if len(resplist) < 1:
        return "Empty: " + str(j)
    else:
        elev = int(round(int(resplist[0]) * 3.28084, 0))
    return elev

def get_airport_item(k_id, item):
    if len(k_id) == 4:
        pass
    elif len(k_id) == 3:
        k_id = 'k' + k_id
    else:
        return None
    req_url = fe_url + '?ids=' + k_id + '&format=json'
    resp = request.urlopen(req_url)
    j = json.load(resp)
    resp.close()
    resplist = []
    for i in j:
        resplist.append(i[item])
    if len(resplist) < 1:
        return "Empty: " + str(j)
    else:
        return resplist[0]



def get_airport_all(k_id):
    if len(k_id) == 4:
        pass
    elif len(k_id) == 3:
        k_id = 'k' + k_id
    else:
        return None
    req_url = fe_url + '?ids=' + k_id + '&format=json'
    resp = request.urlopen(req_url)
    j = json.load(resp)
    resp.close()
    return j[0]

def get_airport_coords(k_id):
    j = get_airport_all(k_id)
    if j == None:
        return None
    return (j['lat'], j['lon'])

def get_distance_4(lat1, lon1, lat2, lon2):
    lat1_rd = math.radians(lat1)
    lon1_rd = math.radians(lon1)
    lat2_rd = math.radians(lat2)
    lon2_rd = math.radians(lon2)
    d = 3440.07 * math.acos(math.sin(lat1_rd)*math.sin(lat2_rd) + 
                            math.cos(lat1_rd)*math.cos(lat2_rd)*math.cos(lon1_rd-lon2_rd))
    return round(d, 1)
    
def get_distance_tp(tp1, tp2):
    return get_distance_4(tp1[0], tp1[1], tp2[0], tp2[1])

def get_gross_weight(ptr):
    ac_items = Ac_item.objects.filter(category__name="Gross Weight").filter(aircraft__id=ptr)
    gw = Ac_value.objects.filter(ac_item__in=ac_items)[0]
    return gw

def get_max_aft_cg(ptr):
    ac_items = Ac_item.objects.filter(category__name="Max Aft CG").filter(aircraft__id=ptr)
    macg = Ac_value.objects.filter(ac_item__in=ac_items)[0]
    return macg


def get_wandb(ptr):
    ac = Aircraft.objects.get(pk=ptr)
    wb_categories = wandb_category.objects.filter(aircraft=ac)
    wb_items = wandb_item.objects.filter(category__in=wb_categories)
    total_moment = 0
    total_weight = 0
    for wb_item in wb_items:
        if wb_item.weight != None:
            total_weight += wb_item.weight
            total_moment += wb_item.weight*wb_item.category.arm
    if total_weight > 0:
        total_arm = (total_moment/total_weight)
    else:
        total_arm = 0
    return {'total_weight':total_weight, 'total_arm':round(total_arm, 2)}

def get_cg_range(ac_ptr, total_weight):
    ac = Aircraft.objects.get(pk=ac_ptr)
    qs = wandb_box_segment.objects.filter(aircraft=ac)
    row_below = qs.filter(gross_weight__lte=total_weight).order_by('-gross_weight').first()
    row_above = qs.filter(gross_weight__gte=total_weight).order_by('gross_weight').first()
    weight_range = row_above.gross_weight - row_below.gross_weight
    assert weight_range > 0, "Weight range less than zero"
    diff_from_floor = total_weight - row_below.gross_weight
    position = diff_from_floor / weight_range

    #mins
    min_cg_range = row_above.min_cg - row_below.min_cg
    assert min_cg_range > 0, "Min CG range less than zero"
    min_cg = (position * min_cg_range) + row_below.min_cg

    assert row_below.max_cg == row_above.max_cg, "Max CG values don't match"
    return (round(min_cg, 2), row_below.max_cg)


def get_tach_log(ac, days_back=29):
    retlist = []
    fls = Flightlogitem.objects.filter(logitem__uta__aircraft=ac).order_by('logitem__date')
    #firstdate = fls.first().logitem.date
    lastdate = fls.last().logitem.date
    firstdate = lastdate - timedelta(days=30)
    this_day = firstdate
    last_tach = 0
    last_tach_tuple = get_latest_tach(ac, this_day)
    last_tach = last_tach_tuple[0]
    while this_day <= lastdate:
        date_fls = fls.filter(logitem__date=this_day)
        if len(date_fls) == 0:
            hours = last_tach 
        else:
            hours = date_fls.last().tach
            last_tach = hours
        retlist.append({'date':this_day, 'hours':hours})
        this_day = this_day + timedelta(days=1)
    return retlist

def get_TTE(ac):
    tte_correction = Ac_item.objects.filter(category__name="Tach Time Correction").filter(aircraft=ac)
    #tte_value = Ac_value.objects.filter(ac_item=tte_correction)
    tte_value = Ac_value.objects.filter(ac_item__category__name="Tach Time Correction").filter(ac_item__aircraft=ac)
    if len(tte_value) == 0:
        return None
    else:
        fls = Flightlogitem.objects.filter(logitem__uta__aircraft=ac).order_by('logitem__date')
        return float(fls.last().tach) + float(tte_value.last().value)

def file_upload(infile, name):
    save_path = os.path.join(default_storage.location, 'uploads', name)
    path = default_storage.save(save_path, infile)
    rp = path[len(settings.MEDIA_ROOT):]
    dsp = default_storage.path(path)
    this_file = File.objects.create(name=name, rel_path=rp)
    this_file.save()
    return this_file.id

def get_path(f):
    
    bn = os.path.basename(f.rel_path)
    dsp = default_storage.path(default_storage.location + '/uploads/' + bn)
    #db_logger.info('file: %s' % str(f))
    #db_logger.info('db path: %s' % str(f.path))
    #db_logger.info('basename: %s' % bn)
    #db_logger.info('dsp: %s' % dsp)
    return dsp

def is_float(string):
    try:
        float(string)
        return True
    except ValueError:
        return False

def get_latest_tach(aircraft, date=date.today()):
    last_flights = Flightlogitem.objects.filter(logitem__uta__aircraft=aircraft).filter(logitem__date__lte=date).order_by('-logitem__date')
    last_maintenances = Maintlogitem.objects.filter(logitem__uta__aircraft=aircraft).filter(logitem__date__lte=date).order_by('-logitem__date')
    last_flight = None
    for lf in last_flights:
        if is_float(lf.tach):
            last_flight = lf
            break
    for lm in last_maintenances:
        if is_float(lm.tach):
            last_maintenance = lm
            break
    if last_flight != None:
        if last_flight.logitem.date >= last_maintenance.logitem.date:
            last_date = last_flight.logitem.date
            last_tach = last_flight.tach
        else:
            last_date = last_maintenance.logitem.date
            last_tach = last_maintenance.tach
    else:
        last_date = last_maintenance.logitem.date
        last_tach = last_maintenance.tach
    return (last_tach, last_date)

def get_angle_difference(heading1, heading2):
    if heading1 == 'VRB':
        heading1 = int(heading2) + 90
        if heading1 > 360:
            heading1 = heading1 - 360
    heading1 = int(heading1)
    heading2 = int(heading2)
    first_diff = abs(heading1 - heading2)
    if first_diff <= 180:
        return first_diff
    second_diff = abs((heading2 + 360) - heading1)
    return second_diff

def get_crosswind(wind, runway):
    wind_speed = int(wind[-2:])
    wind_direction = wind[0:3]
    runway_direction = runway * 10
    angle_difference = get_angle_difference(wind_direction, runway_direction)
    tailwind = False
    if angle_difference > 90:
        #runway = runway + 18 #use other runway
        #if runway > 36:
        #    runway = runway - 36
        #runway_direction = runway * 10
        #angle_difference = get_angle_difference(wind_direction, runway_direction)
        tailwind = True
    rads = math.radians(angle_difference)
    mult = math.sin(rads)
    xw = round(mult*wind_speed, 0)
    direct = False
    if angle_difference >= 80 and angle_difference <= 100:
        direct = True
    return {'speed': xw, 'tailwind':tailwind, 'direction':'unknown', 'direct':direct}

def decode_metar(metar, ret='list'):
    ml = metar.split(" ")
    ml.reverse()
    d = {'other':[], 'ceiling':[]}
    l = []
    while len(ml):
        v = ml.pop()
        if len(v) == 4 and v[0].upper() == 'K':
            d['location'] = v
            l.append({'key':'location', 'value':v})
        elif len(v) == 7 and v[-1:].upper() == 'Z':
            d['time'] = v
            l.append({'key':'time', 'value':v})
        elif len(v) == 7 and v[-2:].upper() == 'KT':
            d['wind_speed'] = v[3:5]
            d['wind_direction'] = v[0:3]
            d['wind'] = v
            l.append({'key':'wind', 'value':v})
        elif len(v) == 10 and v[-2:].upper() == 'KT':
            d['wind_speed'] = v[3:5]
            d['wind_direction'] = v[0:3]
            gust_speed = v.split("G")[1][0:2]
            d['gusts'] = gust_speed
            d['wind'] = v
            l.append({'key':'wind', 'value':v})
            l.append({'key':'gusts', 'value':gust_speed})
        elif v[-2:] == 'SM':
            #d['visibility'] = v.split('SM')[0]
            d['visibility'] = v
            l.append({'key':'visibility', 'value':v})
        elif v[0:3].upper() in [ 'BKN', 'OVC', 'FEW', 'SCT', 'CLR' ]:
            d['ceiling'].append(v)
            l.append({'key':'ceiling', 'value':v})
        elif '/' in v:
            s = v.split('/')
            if len(s) > 2:
                continue
            t = s[0]
            if t.isnumeric():
                d['temp'] = t
                l.append({'key':'temp', 'value':t})
                dp = s[1]
                dp.replace('M', '-')
                dp.replace('m', '-')
                d['dewpoint'] = dp
                l.append({'key':'dewpoint', 'value':dp})
            else:
                continue
        elif len(v) == 5 and v[0].upper() == 'A':
            d['altimeter'] = v
            l.append({'key':'altimeter', 'value':v})
        elif len(v) == 7 and v[3].upper() == 'V':
            d['clocking'] = v
            l.append({'key':'clocking', 'value':v})
        elif v.upper() == 'RMK':
            d['remarks'] = []
            while len(ml) > 0:
                w = ml.pop()
                d['remarks'].append(w)
                l.append({'key':'remarks', 'value':w})
        else:
            d['other'].append(v)
            l.append({'key':'other', 'value':v})
    lowest_ceiling = 60000
    for val in d['ceiling']:
        t = val[0:3].upper()
        if t == 'CLR':
            break
        h = int(val[3:6]) * 100
        if t in ['BKN', 'OVC']:
            if h < lowest_ceiling:
                lowest_ceiling = h
    l.append({'key':'lowest_ceiling', 'value':lowest_ceiling})
    d['lowest_ceiling'] = lowest_ceiling
    if ret == 'list':
        return l
    else:
        return d




def get_alt_setting(altimeter):
    #data validation
    if isinstance(altimeter, int):
        #print("Is int")
        altimeter = altimeter/100
    elif isinstance(altimeter, float):
        #print("Is float")
        pass
    elif isinstance(altimeter, str):
        #print("Is string")
        if "." in altimeter:
            try:
                t = float(altimeter)
            except ValueError:
                #print("Str not numeric")
                return altimeter
            altimeter = t
        else:
            try:
                t = int(altimeter)
            except ValueError:
                #print("Str was not int")
                return altimeter
            altimeter = float(altimeter[0:2] + "." + altimeter[2:4])
    if 29.0 <= altimeter and 31.0 >= altimeter:
        return altimeter
    else:
        return str(altimeter)
    
def get_pressure_alt(elev, altimeter):
    alt = get_alt_setting(altimeter)
    if isinstance(alt, str):
        return "Altimeter invalid: %s" % alt
    if not isinstance(elev, int):
        return "Elevation invalid: %s" % str(elev)
    alt_ratio = alt/29.92126
    ar_exp = alt_ratio**0.190261
    mult = 1 - ar_exp
    correction = 145442.2 * mult
    pa = int(round(elev + correction, 0))
    return pa

def get_ISA(elevation):
    if not isinstance(elevation, int):
        return "Elevation invalid: %s" % str(elevation)
    corr = round((elevation/1000)*2, 0)
    isa = 15 - corr
    return isa

def get_density_alt(pa, temp):
    dev = (int(temp) - get_ISA(pa))
    corr = 120 * dev
    da = round(pa + corr, 0)
    return da

def get_cloudbase(temp, dewpoint): #this is above field elevation.
                                    #so you still have to add field elev to get MSL
    spread = int(temp) - int(dewpoint)
    div = spread/2.5
    mult = div*1000
    return int(round(mult, 0))

def get_dewpoint_int(dp):
    if 'M' in dp[0].upper():
        return int("-" + dp[1:])
    else:
        return int(dp)

def get_landings(user, num_days, t='day'):
    num_days = -1*num_days
    if t == 'day':
        field = 'day_landings'
    elif t == 'night':
        field = 'night_landings'
    else:
        return 0
    ret_field = field + '__sum'
    d = date.today() + timedelta(num_days)
    flights = Flightlogitem.objects.filter(logitem__uta__user=user).filter(logitem__date__gte=d)
    landings = flights.aggregate(Sum(field))
    retval = landings[ret_field]
    if retval == None:
        retval = 0
    return retval

def get_currency_deadline(user, t='day'):
    landings = 0
    flights = Flightlogitem.objects.filter(logitem__uta__user=user).order_by('-logitem__date')
    for f in flights:
        if t == 'day':
            landings += f.day_landings
        elif t == 'night':
            landings += f.night_landings
        else:
            return None
        if landings >= 3:
            last_day = f.logitem.date + timedelta(90)
            return last_day
    

def get_latest_ttaf(aircraft, date=date.today()):
    adjusts = Tach_adjust.objects.filter(firstlog__logitem__uta__aircraft=aircraft, category='airframe').filter(firstlog__logitem__date__lte=date).order_by('firstlog__date')
    last_flights = Flightlogitem.objects.filter(logitem__uta__aircraft=aircraft).filter(logitem__date__lte=date).order_by('-logitem__date')
    last_maintenances = Maintlogitem.objects.filter(logitem__uta__aircraft=aircraft).filter(logitem__date__lte=date).order_by('-logitem__date')
    last_flight = None
    for lf in last_flights:
        if is_float(lf.tach):
            last_flight = lf
            break
    for lm in last_maintenances:
        if is_float(lm.tach):
            last_maintenance = lm
            break
    if last_flight != None:
        if last_flight.logitem.date >= last_maintenance.logitem.date:
            last_date = last_flight.logitem.date
            last_tach = last_flight.tach
        else:
            last_date = last_maintenance.logitem.date
            last_tach = last_maintenance.tach
    else:
        last_date = last_maintenance.logitem.date
        last_tach = last_maintenance.tach
    if len(adjusts) == 0:
        return last_tach
    last_adjust = adjusts.last()
    return round(float(last_tach) + float(last_adjust.hours), 1)
    
def get_ttaf_at_date(date):
    adjusts = Tach_adjust.objects.filter(firstlog__logitem=mi.logitem, category='airframe').order_by('firstlog__date')
    if len(adjusts) == 0:
        if is_float(mi.tach):
            return mi.tach
        else:
            maint_items = Maintlogitem.objects.filter(logitem__date__lt=mi.logitem.date).order_by('-logitem__date')
            for mi in maint_items:
                if is_float(mi.tach):
                    return mi.tach
    last_adjust = adjusts.last()
    return float(last_tach) + float(last_adjust.hours)

