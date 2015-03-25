"""
environment.py defines setup and teardown behaviors for behave tests.
The behavior in this file is appropriate for integration tests, and
could be used to bootstrap other integration tests in our project.
It sets up a test server and test database by using the LiveServerTestCase
machinery.
"""
from behave import *
from httplib import CannotSendRequest
from selenium import webdriver
from urlparse import urljoin

from django.test.testcases import LiveServerTestCase

from kalite.testing.behave_helpers import login_as_admin, logout

def before_all(context):

    # So we get a free test server and test database, with appropriate
    # setup and teardown methods
    hijacked_test_case = context.hijacked_test_case = HijackTestCase()
    hijacked_test_case.setUpClass()
     
    def browser_url(url):
        return urljoin(hijacked_test_case.live_server_url, url)
    
    context.browser_url = browser_url


def after_all(context):
    context.hijacked_test_case.tearDownClass()


def before_feature(context, feature):
    context.logged_in = False
    if "as_admin" in feature.tags:
        context.logged_in = True
        login_as_admin(context)


def after_feature(context, feature):
    if context.logged_in:
        logout(context)


def before_scenario(context, scenario):
    browser = context.browser = webdriver.Firefox()
    # _pre_setup flushes the databse, so we run it before every scenario
    context.hijacked_test_case._pre_setup()


def after_scenario(context, scenario):
    context.hijacked_test_case._post_teardown()
    try:
        context.browser.quit()
    except CannotSendRequest:
        pass


class HijackTestCase(LiveServerTestCase):

    def runTest(self):
        pass
