#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import getpass
import json
import os
import sys
from urllib.request import urlopen
from urllib.parse import urlencode

import vk_auth

API_VERSION = '5.44'

def call_api(method, params, token):
    params['v'] = API_VERSION
    params['access_token'] = token
    encoded_params = urlencode(list(params.items()))
    api_url = 'https://api.vk.com/method/{method}?{params}'
    url = api_url.format(method=method, params=encoded_params)
    response = urlopen(url).read()
    response = response.decode('utf-8', 'replace')
    json_response = json.loads(response)
    if 'response' not in json_response:
        pretty_json = json.dumps(json_response['error'], indent=2)
        raise RuntimeError('query failed: {0}'.format(pretty_json))
    return json_response["response"]


def get_albums(user_id, token):
    return call_api('photos.getAlbums', {'owner_id': user_id, 'need_system': 1}, token)['items']


photo_sizes = [
    'photo_2560',
    'photo_1280',
    'photo_807',
    'photo_604',
    'photo_130',
    'photo_75'
]


def get_largest_photo_url(photo):
    for size_key in photo_sizes:
        if size_key in photo:
            return photo[size_key]
    pretty_json = json.dumps(photo, indent=2)
    raise RuntimeError('No photo url found in {0}'.format(pretty_json))


def get_photos_urls(user_id, album_id, token):
    photos_list = call_api('photos.get', {'owner_id': user_id, 'album_id': album_id}, token)
    return [get_largest_photo_url(photo) for photo in photos_list['items']]


def save_photos(urls, directory):
    if not os.path.exists(directory):
        os.mkdir(directory)
    pad_length = len(str(len(urls)))
    names_pattern = '{0:0>{width}}.jpg'
    for num, url in enumerate(urls):
        filename = names_pattern.format(num + 1, width=pad_length)
        filepath = os.path.join(directory, filename)
        print('Downloading ', filepath)
        open(filepath, 'wb').write(urlopen(url).read())


directory = None
if len(sys.argv) == 2:
    directory = sys.argv[1]
email = input('Email: ')
password = getpass.getpass()
client_id = '2951857'  # Vk application ID
token, user_id = vk_auth.auth(email, password, client_id, 'photos')
albums = get_albums(user_id, token)
print('\n'.join('{0}. {1}'.format(str(num + 1), album['title']) for num, album in enumerate(albums)))
choice = None
while choice not in range(len(albums)):
    choice = int(input('Choose album number: ')) - 1
if not directory:
    directory = albums[choice]['title']
photos_urls = get_photos_urls(user_id, albums[choice]['id'], token)
save_photos(photos_urls, directory)
