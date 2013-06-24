"""
These will be run when you run "manage.py test [central].
These require a test server to be running, and multiple ports
  need to be available.  Run like this:
./manage.py test central --liveserver=localhost:8004-8010
".
"""

#import logging
#from selenium import webdriver
#from selenium.common.exceptions import NoSuchElementException

from selenium.webdriver.common.keys import Keys

from django.contrib.auth.models import User

import settings
from registration.models import RegistrationProfile
from utils.testing.decorators import central_only
from utils.testing.browser import BrowserTestCase


class KALiteCentralBrowserTestCase(BrowserTestCase):
    """
    Base class for browser-based central server test cases.
    """

    def register_user(self, username, password, first_name="firstname", last_name="lastname", org_name="orgname", expect_success=True):
        """Registers a user on the central server (and performs relevant checks, unless expect_success=False)"""
         
        register_url = self.reverse("registration_register")

        self.browse_to(register_url) # Load page
        self.assertIn("Sign up", self.browser.title, "Register page title")
        
        # Part 1: REGISTER
        self.browser_activate_element(id="id_first_name") # explicitly set the focus, to start
        self.browser_send_keys(first_name + Keys.TAB) # first name
        self.browser_send_keys(last_name + Keys.TAB) # last name
        self.browser_send_keys(username + Keys.TAB) #email
        self.browser_send_keys(org_name + Keys.TAB) #org name
#        self.browser_send_keys(Keys.TAB) #org expansion link
        self.browser_send_keys(password + Keys.TAB) #password
        self.browser_send_keys(password + Keys.TAB) #password (again)
        self.browser_send_keys(Keys.TAB) #newsletter subscription
        self.browser_send_keys(Keys.SPACE + Keys.TAB) # checkbox 1
        self.browser_send_keys(Keys.SPACE + Keys.TAB) # checkbox 2

        # We could capture the activation link, but we'll just cheat
        #   by querying the value directly in the "activate user" function.
        self.browser_send_keys(Keys.RETURN)
        
        
        # Make sure that the page changed to the "thank you" confirmation page
        if expect_success:
            self.assertTrue(self.wait_for_page_change(register_url), "RETURN causes page to change")
            self.assertIn(self.reverse("registration_complete"), self.browser.current_url, "Register browses to thank you page" )
            self.assertIn("Registration complete", self.browser.title, "Check registration complete title")



    def activate_user(self, username, expect_success=True):
        """Activates a user account on the central server (and performs relevant checks, unless expect_success=False)"""
        
        # Get the activation url, then browse there.
        user = User.objects.get(username=username)
        profile = RegistrationProfile.objects.get(user=user)
        activation_key = profile.activation_key
        self.assertNotEqual(activation_key, "ALREADY_ACTIVATED", "Make sure the user wasn't already activated.")
        
        activation_url = self.reverse('registration_activate', kwargs={ 'activation_key': activation_key });
        self.browse_to(activation_url)
        
        # Verify what we see!
        if expect_success:
            self.check_django_message(message_type="success", contains="Your account is now activ", num_messages=1)


    def login_user(self, username, password, expect_success=True):
        """Logs a user account in to the central server (and performs relevant checks, unless expect_success=False)"""

        login_url = self.reverse("auth_login")
        self.browse_to(login_url) # Load page
        self.assertIn("Log in", self.browser.title, "Login page title")
        
        # Focus should be on username, pasword and submit
        #   should be accessible through keyboard only.
        self.browser.find_element_by_id("id_username").clear()
        self.browser.find_element_by_id("id_username").click() # explicitly set the focus, to start
        self.browser.switch_to_active_element().send_keys(username + Keys.TAB)
        self.browser.switch_to_active_element().send_keys(password + Keys.TAB)
        self.browser.switch_to_active_element().send_keys(Keys.RETURN)
        
        # Make sure that the page changed to the admin homepage
        if expect_success:
            self.assertTrue(self.wait_for_page_change(login_url), "RETURN causes page to change")
            self.assertIn(self.reverse("homepage"), self.browser.current_url, "Login browses to homepage (account admin)" )
            self.assertIn("Account administration", self.browser.title, "Check account admin page title")

        
    def logout_user(self, expect_success=True):
        """Logs a user account out of the central server (and performs relevant checks, unless expect_success=False)"""
        
        # Nothing to do if they're not logged in!
        if not self.is_logged_in():
            return
        
        # To avoid detection of page changes, do different things based on the 
        #   (assumed) server redirect after logout happens.
        if self.reverse("homepage") in self.browser.current_url:
            self.browser.get(self.reverse("auth_logout"))
        else:
            self.browse_to(self.reverse("auth_logout"))
    
        if expect_success:
            self.assertIn(self.reverse("homepage"), self.browser.current_url, "Logout browses to homepage" )
            self.assertFalse(self.is_logged_in(), "Make sure that user is no longer logged in.")


    def is_logged_in(self, username=None):
        """Checks if a user account is logged in to the central server."""
        elements = self.browser.find_elements_by_id("logout")
        
        if len(elements)==0:
            return False
        elif username is None:
            return True
        else:
            return elements[0].text.startswith(username + " ")
        
        

@central_only
class SuperUserTest(KALiteCentralBrowserTestCase):
    """Log in the super user"""

    def test_superuser_login(self):
        """
        Tests that an existing admin user can log in.
        """

        self.login_user(self.admin_user.username, "test")


@central_only
class OrgUserRegistrationTest(KALiteCentralBrowserTestCase):
    user_email = "test_user@nowhere.com"
    password   = "password"

    def test_user_register(self):
        """Tests that a user can register"""
         
        self.register_user(username=self.user_email, password=self.password)


@central_only
class UserRegistrationCaseTest(KALiteCentralBrowserTestCase):
    user_email = "test_user@nowhere.com"
    password   = "password"

    def test_register_login_exact(self):
        """Tests that a user can login with the exact same email address as registered"""
         
        # Register user in one case
        self.register_user(username=self.user_email.lower(), password=self.password)
        self.activate_user(username=self.user_email.lower())

        # Login in the same case
        self.login_user(username=self.user_email.lower(), password=self.password)
        self.logout_user()

        
    def test_login_mixed(self):
        """Tests that a user can login with the uppercased version of the email address that was registered"""
         
        # Register user in one case
        self.register_user(username=self.user_email.lower(), password=self.password)
        self.activate_user(username=self.user_email.lower())

        # Login in the same case
        self.login_user(username=self.user_email.upper(), password=self.password)
        self.logout_user()
        

    def test_register_mixed(self):
        """Tests that a user cannot re-register with the uppercased version of an email address that was registered"""
        
        # Register user in one case
        self.register_user(username=self.user_email.lower(), password=self.password)
        self.activate_user(username=self.user_email.lower())

        # Try to register again in a different case
        self.register_user(username=self.user_email.upper(), password=self.password, expect_success=False)

        text_box = self.browser.find_element_by_id("id_email") # form element        
        error    = text_box.parent.find_elements_by_class_name("errorlist")[-1]
        self.assertIn("This email address is already in use.", error.text, "Check 'email is in use' error.")


    def test_login_two_users_different_cases(self):
        """Tests that a user cannot re-register with the uppercased version of an email address that was registered"""
        
        user1_uname = self.user_email.lower()
        user2_uname = "a"+self.user_email.lower()
        user1_password = self.password
        user2_password = "a"+self.password
        user1_fname = "User1"
        user2_fname = "User2"
        
        # Register & activate two users with different usernames / emails
        self.register_user(username=user1_uname, password=user1_password, first_name=user1_fname)
        self.activate_user(username=user1_uname)
        self.login_user(   username=user1_uname, password=user1_password)
        self.logout_user()
        
        self.register_user(username=user2_uname, password=user2_password, first_name=user2_fname)
        self.activate_user(username=user2_uname)
        self.login_user(   username=user2_uname, password=user2_password)
        self.logout_user()
        
        # Change the second user to be a case-different version of the first user
        user2 = User.objects.get(username=user2_uname)
        user2_uname = user1_uname.upper()
        user2.username = user2_uname
        user2.email = user2_uname
        user2.save()
        
        # First, make sure that user 1 can only log in with user 1's email/password
        self.login_user( username=user1_uname, password=user1_password) # succeeds
        errors = self.browser.find_elements_by_class_name("login_error")
        self.assertEqual(len(errors), 0, "No login errors on successful login.")
        self.logout_user()
        
        self.login_user( username=user2_uname, password=user1_password, expect_success=False) # fails
        errors = self.browser.find_elements_by_class_name("login_error")
        self.assertEqual(len(errors), 1, "Login errors on failed login.")
        self.assertIn("Incorrect user name or password", errors[0].text, "Error text on failed login.")
        
        # Now, check the same in the opposite direction.
        self.login_user( username=user2_uname, password=user2_password) # succeeds
        errors = self.browser.find_elements_by_class_name("login_error")
        self.assertEqual(len(errors), 0, "No login errors on successful login.")
        self.logout_user()

        self.login_user( username=user1_uname, password=user2_password, expect_success=False) # fails
        errors = self.browser.find_elements_by_class_name("login_error")
        self.assertEqual(len(errors), 1, "Login errors on failed login.")
        self.assertIn("Incorrect user name or password", errors[0].text, "Error text on failed login.")
