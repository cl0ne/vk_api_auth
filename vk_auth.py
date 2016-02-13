#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import urllib.request as request
from html.parser import HTMLParser
from urllib.parse import urlparse, urlencode
from http.cookiejar import CookieJar

API_VERSION = '5.44'


class FormParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.url = None
        self.params = {}
        self.in_form = False
        self.form_parsed = False
        self.method = "GET"

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "form":
            if self.form_parsed:
                raise RuntimeError("Second form on page")
            if self.in_form:
                raise RuntimeError("Already in form")
            self.in_form = True
        if not self.in_form:
            return
        attrs = dict((name.lower(), value) for name, value in attrs)
        if tag == "form":
            self.url = attrs["action"]
            if "method" in attrs:
                self.method = attrs["method"].upper()
        elif tag == "input" and "type" in attrs and "name" in attrs:
            if attrs["type"] in ["hidden", "text", "password"]:
                self.params[attrs["name"]] = attrs["value"] if "value" in attrs else ""

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "form":
            if not self.in_form:
                raise RuntimeError("Unexpected end of <form>")
            self.in_form = False
            self.form_parsed = True


def auth(email, password, client_id, scope):
    def split_key_value(kv_pair):
        kv = kv_pair.split("=")
        return kv[0], kv[1]

    # Authorization form
    def auth_user(email, password, client_id, scope, opener):
        request_params = {
            'redirect_uri': 'https://oauth.vk.com/blank.html',
            'response_type': 'token',
            'client_id': client_id,
            'display': 'mobile',
            'scope': ','.join(scope),
            'v': API_VERSION
        }
        base_auth_url = 'https://oauth.vk.com/authorize'
        params = list(request_params.items())
        params = urlencode(params).encode('utf-8')
        response = opener.open(base_auth_url, params)
        doc = response.read().decode(encoding='utf-8', errors='replace')
        parser = FormParser()
        parser.feed(doc)
        parser.close()
        if (not parser.form_parsed or
                parser.url is None or
                "pass" not in parser.params or
                "email" not in parser.params):
            raise RuntimeError("Something wrong")
        parser.params["email"] = email
        parser.params["pass"] = password
        if parser.method == "POST":
            params = urlencode(parser.params).encode('utf-8')
            response = opener.open(parser.url, params)
        else:
            raise NotImplementedError("Method '%s'" % parser.method)
        doc = response.read().decode(encoding='utf-8', errors='replace')
        return doc, response.geturl()

    # Permission request form
    def give_access(doc, opener):
        parser = FormParser()
        parser.feed(doc)
        parser.close()
        if not parser.form_parsed or parser.url is None:
            raise RuntimeError("Something wrong")
        if parser.method == "POST":
            params = urlencode(parser.params).encode('utf-8')
            response = opener.open(parser.url, params)
        else:
            raise NotImplementedError("Method '{0}'".format(parser.method))
        return response.geturl()

    if not isinstance(scope, list):
        scope = [scope]

    opener = request.build_opener(
            request.HTTPCookieProcessor(CookieJar()),
            request.HTTPRedirectHandler())
    doc, url = auth_user(email, password, client_id, scope, opener)
    if urlparse(url).path != "/blank.html":
        # Need to give access to requested scope
        url = give_access(doc, opener)
    if urlparse(url).path != "/blank.html":
        raise RuntimeError("Expected success here")
    answer = dict(split_key_value(kv_pair) for kv_pair in urlparse(url).fragment.split("&"))
    if "access_token" not in answer or "user_id" not in answer:
        raise RuntimeError("Missing some values in answer")
    return answer["access_token"], answer["user_id"]
