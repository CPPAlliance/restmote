import requests
import logging
from urllib.parse import urlparse
from urllib.parse import urljoin
import re

from django.conf import settings

restmote_remote_ids=[]

root = urljoin(settings.RESTMOTE_HOST + ":" + settings.RESTMOTE_PORT, settings.RESTMOTE_API_ROOT)

def get_data(url):
    if hasattr(settings, "RESTMOTE_USER") and hasattr(settings, "RESTMOTE_PASSWORD"):
        r = requests.get(url, timeout=15, auth=(settings.RESTMOTE_USER, settings.RESTMOTE_PASSWORD))
    else:
        r = requests.get(url, timeout=15)
    if r.status_code == 200:
        logging.info(url)
        logging.info(r.json())
        if r.links.get('next'):
            nexturl=r.links['next']['url']
        else:
            nexturl=None
        return True, r.json(), nexturl
    else:
        logging.info("Connection failed: %s" % r.text)
        return False, []


def build_objects(obj_class, data, field_bindings, static_field_bindings={}, remote_id='id', local_id='id', nested=[]):
    global restmote_remote_ids
    for e in data:

        if e[remote_id] not in restmote_remote_ids:
            restmote_remote_ids.append(e[remote_id])

        try:
            o = obj_class.objects.get(**{local_id: e[remote_id]})
        except obj_class.DoesNotExist:
            o = obj_class()

        for f in [x for x in e if x in field_bindings]:
            setattr(o, field_bindings[f], e[f])

        for n in nested:
            for f in [x for x in e[n] if x in field_bindings]:
                setattr(o, field_bindings[f], e[n][f])

        for x in static_field_bindings:
            setattr(o, x, static_field_bindings[x])

        setattr(o, local_id, e[remote_id])
        o.save()
        logging.info("Added %s: %s" % (local_id, o.pk))


def sync_objects(url, qfilter, obj_class, field_bindings, static_field_bindings={}, remote_id='id', local_id='id', nested=[]):
    if '?' in url:
        querytoken='&';
    else:
        querytoken='?';
    if re.match("^https://", url) or re.match("^http://", url):
        targeturl=url
    else:
        targeturl=root + url

    status, data, nexturl = get_data(targeturl + querytoken + qfilter)
    if status:
        build_objects(obj_class, data, field_bindings, static_field_bindings=static_field_bindings, remote_id=remote_id, local_id=local_id, nested=nested)
        if nexturl:
            sync_objects(nexturl, qfilter, obj_class, field_bindings, static_field_bindings=static_field_bindings, remote_id=remote_id, local_id=remote_id, nested=nested)
        return 1
    else:
        return 0

def remove_objects_v1(url, obj_class, obj_string):
    """
    The 'original' version of remove_objects.
    Didn't take pagination of results into account. Seemed to have other bugs also.
    Use full_sync and new remove_objects instead.
    """
    status, remote_ids, nexturl = get_data(root + url)
    if status:
        local_ids = obj_class.objects.values_list('id' + obj_string, flat=True)
        must_remove = list(set(local_ids).difference(remote_ids))
        obj_class.objects.filter(**{'id' + obj_string + '__in': must_remove}).delete()
        if must_remove:
            logging.info("Deleted %s: %s" % (obj_string, ', '.join(str(x) for x in must_remove)))
        return 1
    else:
        return 0

def remove_objects(obj_class, local_id='id', rfilter={}):
    """
    Prune items from database table after a sync.
    Because this is comparing against discovered remote values, it must be run in conjunction with sync_objects. Thus, calling it from within full_sync.
    """
    local_ids = obj_class.objects.filter(**rfilter).values_list(local_id, flat=True)
    must_remove = list(set(local_ids).difference(restmote_remote_ids))
    obj_class.objects.filter(**{local_id + '__in': must_remove}).delete()
    if must_remove:
        logging.info("Deleted %s: %s" % (local_id, ', '.join(str(x) for x in must_remove)))

def full_sync(url, qfilter, obj_class, field_bindings, static_field_bindings={}, remote_id='id', local_id='id', rfilter={}, nested=[]):
    global restmote_remote_ids
    restmote_remote_ids=[]
    sync_objects(url, qfilter, obj_class, field_bindings, static_field_bindings=static_field_bindings, remote_id=remote_id, local_id=local_id, nested=nested)
    remove_objects(obj_class, local_id=local_id, rfilter=rfilter)
