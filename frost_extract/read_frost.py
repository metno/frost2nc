import json
import logging
import os
import sys
import urllib
import urllib.request
import urllib.error
from datetime import datetime, date
from dateutil.relativedelta import relativedelta


class FrostApi(object):

    def __init__(self, base_url, user_id):
        password_manager = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        password_manager.add_password(None, base_url, user_id, '')
        handler = urllib.request.HTTPBasicAuthHandler(password_manager)
        self._url_opener = urllib.request.build_opener(handler)
        
        if base_url.endswith('/'):
            base_url = base_url[:-1]
        self._base_url = base_url
        
        self._elements_cache = {}

    def _timerange_format(self, time_range):
        format = lambda t: datetime.strftime(t, '%Y-%m-%dT%H:%M:%SZ')
        return format(time_range[0]) + '/' + format(time_range[1])

    def get_available_elements(self, station, time_range, element_filter):
        args = {'sources': station,
                'elements': ','.join(element_filter),
                'referencetime': self._timerange_format(time_range)
                }

        url = self._create_query('observations/availableTimeSeries', **args)
        return self._execute_query(url)

    def get_data(self, station, elements, time_range):
        time_from = time_range[0]
        time_to = time_range[1]
        
        arguments = {
            'sources': station,
            'elements': ','.join([e['elementId'] for e in elements])
            }
        # if 'level' in element:
        #     arguments['levels'] = element['level']['value']            
        return self._get_data(time_from, time_to, arguments)

    def get_source(self, station):
        if station:
            url = self._create_query('sources', ids=station)
            return self._make_single_return_value_query(url)
        else:
            url = self._create_query('sources')
            return self._execute_query(url)

    def get_elements(self):
        url = self._create_query('elements')
        return self._execute_query(url)
                
    def _get_data(self, time_from, time_to, args, retried_on=[]):
        try:
            args['referencetime'] = self._timerange_format((time_from, time_to))
            url = self._create_query('observations', **args)
            return self._execute_query(url)
        except urllib.error.HTTPError as e:
            code = e.getcode()
            if code == 404:
                # no data
                return []
            else:
                if code not in retried_on:
                    logging.warning('Got %d from server, retrying' % (code,))
                    return self._get_data(time_from, time_to, args, retried_on + [code])
                else:
                    raise

    def _create_query(self, service, **parameters):
        ret = self._base_url + '/' + service + '/v0.jsonld?' + urllib.parse.urlencode(parameters)
        logging.debug(ret)
        return ret
        
    def _execute_query(self, url):
        logging.getLogger(__name__).debug(url)
        response = self._url_opener.open(url)
        ret = json.loads(str(response.read(), 'utf8'))['data']
        return ret

    def _make_single_return_value_query(self, url):
        ret = self._execute_query(url)
        if not ret:
            raise KeyError('No data returned for url: ' + url)
        return ret[0]





def save(frost, station, wanted_elements, time_range, base_folder):
    try:
        elements = frost.get_available_elements(station, time_range, wanted_elements)
    except urllib.error.HTTPError as e:
        if e.getcode() != 404:
            logging.warning(e)
        return []

    lowest_time = min([datetime.strptime(e['validFrom'][:7], '%Y-%m').date() for e in elements])
    time_from = max(lowest_time, time_range[0])
    time_to = time_range[1]
    tr = time_from, time_to

    if tr != time_range:
        logging.info('Adjusting time range to %s - %s to match actual observations' % tr)
        time_range = tr

    files = []
    for period in _time_iter(time_range):
        try:
            d = frost.get_data(station, elements, period)
            file_name = get_file_name(base_folder, station, period)
            os.makedirs(os.path.dirname(file_name), exist_ok=True)
            with open(file_name, 'w') as f:
                json.dump(d, f)
            files.append(file_name)
        except urllib.error.HTTPError as e:
            if e.getcode() != 404:
                logging.warning(e)
    files.reverse()
    return files


def _time_iter(time_range, offset=relativedelta(months=1)):
    if time_range:
        start = time_range[1]
        end = time_range[0]
    else:
        start = date(2018,3,1)
        end = date(1850, 1, 1)
    while start > end:
        next = start - offset
        sys.stderr.write('\r%s - %s' % (next, start))
        yield next, start
        start = next


def get_folder(base_folder, station):
    return '%s/%s/' % (base_folder, station)

def get_file_name(base_folder, station, time_range):
    ret = '%s/%s/%s.json' % (get_folder(base_folder, station), time_range[0].year, datetime.strftime(time_range[0], '%m'))
    return ret
