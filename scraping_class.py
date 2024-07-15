import random
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.service import Service

from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

"""Scraping class with scraping tools as random useragent, random wait and complex methods"""


class ScrapingClass:
    def __init__(self):
        self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))

    """
    Simple methods from the driver class
    """

    def get(self, url):
        """Runs the get method from selenium.webdriver with random wait
        Args:
            url (str): target url
        """
        self.driver.get(url)
        self.wait(1, 1)

    def click_xpath(self, xpath):
        """Moves to the element matching the xpath and wait before clicking on it
        Args:
            xpath (str): element xpath
        """
        self.driver.find_element(By.XPATH, value=xpath).click()
        self.wait(1, 1.2)

    def no_wait_click_xpath(self, xpath):
        """Moves to the element matching the xpath and wait before clicking on it
        Args:
            xpath (str): element xpath
        """
        self.driver.find_element(by=By.XPATH, value=xpath).click()

    def click_css_selector(self, selector):
        """
        Moves to the element matching the selector and wait before clicking on it
        Args:
            selector (str): element selector
        """
        self.driver.find_element(by=By.CSS_SELECTOR, value=selector).click()
        self.wait(0.1, 1)

    def close(self):
        """Runs the close method from selenium.webdriver"""
        self.driver.close()

    def quit(self):
        self.driver.quit()

    def get_html(self):
        return self.driver.execute_script("return document.body.innerHTML;")

    def find_element_by_xpath(self, xpath):
        """Runs the find_element_by_xpath method from selenium.webdriver
        Args:
            xpath (str): element xpath
        """
        return self.driver.find_element(by=By.XPATH, value=xpath)

    def find_element_by_xpath_2(self, xpath):
        """Runs the find_element_by_xpath method from selenium.webdriver
        Args:
            xpath (str): element xpath
        """
        return WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )

    def find_elements_by_xpath(self, xpath):
        """Runs the find_element_by_xpath method from selenium.webdriver
        Args:
            xpath (str): element xpath
        """
        return self.driver.find_elements(by=By.XPATH, value=xpath)

    def find_elements_by_xpath_2(self, xpath):
        """Runs the find_element_by_xpath method from selenium.webdriver
        Args:
            xpath (str): element xpath
        """
        return WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )

    def find_element_by_tag_name(self, tag):
        """Runs the find_element_by_tag_name method from selenium.webdriver
        Args:
            tag (str): element tag name
        """
        return self.driver.find_element(by=By.TAG_NAME, value=tag)

    def move_to_element(self, selector):
        """Moves to the element matching the xpath to make it interactable with
        Args:
            xpath (str): element xpath
        """
        self.driver.execute_script(
            "arguments[0].scrollIntoView(true);",
            WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, selector))
            ),
        )

    def get_dropdown_options(self, xpath):
        """Returns a list with every options object availbale in the dropdown matching the xpath
        Args:
            xpath (str): dropdown xpath
        Returns:
            list: list of options object
        """
        return self.find_element_by_xpath(xpath).find_elements_by_tag_name("option")

    def get_dropdown_options_2(self, xpath):
        """Returns a list with every options object availbale in the dropdown matching the xpath
        Args:
            xpath (str): dropdown xpath
        Returns:
            list: list of options object
        """
        return (
            WebDriverWait(self.driver, 10)
            .until(EC.presence_of_element_located((By.XPATH, xpath)))
            .find_elements(by=By.TAG_NAME, value="option")
        )

    def click_keyboard_enter(self):
        """Click on ENTER"""
        self.find_element_by_tag_name("html").send_keys(Keys.ENTER)

    """
    Waiting methods
    """

    def wait(self, mini, maxi):
        """Wait a random amount of time between maxi seconds and mini seconds (same type but int not mandatory)
        Args:
            mini (int or float): minimum amount of time
            maxi (int or float): maximum aount of time
        """
        time.sleep(mini + random.random() * (maxi - mini))

    def wait_until(self, xpath, condition):
        """Not currently working"""
        WebDriverWait(self.driver, 20).until(condition((By.XPATH, xpath))).click()

    """
    Complex methods
    """

    def move_and_click_xpath(self, xpath):
        """Moves to the element matching the xpath and wait before clicking on it
        Args:
            xpath (str): element xpath
        """
        self.move_to_element(xpath)
        self.wait(0.5, 2)
        self.click_xpath(xpath)
        self.wait(0.5, 2)

    def move_and_click_xpath_2(self, xpath):
        """Moves to the element matching the xpath and wait before clicking on it
        Args:
            xpath (str): element xpath
        """
        self.move_to_element(xpath)
        self.wait(0.5, 1)
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        ).click()
        self.wait(0.5, 1)

    def send_xpath(self, xpath, value):
        """Sends value to the form matching the xpath after clearing it
        Args:
            xpath (str): form xpath
            value (str or int): value to send
        """
        box = self.find_element_by_xpath(xpath)
        box.clear()
        box.send_keys(value)
        self.wait(0.5, 2)

    def send_xpath_2(self, xpath, value):
        """Sends value to the form matching the xpath after clearing it
        Args:
            xpath (str): form xpath
            value (str or int): value to send
        """
        box = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        box.clear()
        box.send_keys(value)
        self.wait(0.5, 1)

    def click_xpath_if_possible(self, xpath):
        action_click = True
        while action_click:
            try:
                self.no_wait_click_xpath(xpath)
            except:
                action_click = False

    def wait_until_click_selector(self, selector):
        self.driver.execute_script(
            "arguments[0].click();",
            WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            ),
        )

    def choose_from_dropdown(self, xpath, index=0, text=None, value=None):
        """Chooses an option from the dropdown matching the xpath. The option can be chosen by index, visible text or value. By defaut the first option is chosen.
        Args:
            xpath (str): dropdown xpath
            index (int, optional): index of the option. Defaults to 0.
            text (str, optional): text of the option. Defaults to None.
            value (int or str, optional): value of the option. Defaults to None.
        """
        self.move_to_element(xpath)
        self.wait(0.5, 1)

        if value != None:
            Select(self.find_element_by_xpath(xpath)).select_by_value(str(value))
        elif text != None:
            Select(self.find_element_by_xpath(xpath)).select_by_visible_text(text)
        else:
            Select(self.find_element_by_xpath(xpath)).select_by_index(index)

    def scroll_down(self):
        """Scroll down to the end of the page (to the last loaded content if the page is infinite)"""
        self.find_element_by_tag_name("html").send_keys(Keys.END)
        self.wait(0.5, 2)

    def scroll_up(self):
        """
        Scroll up to the top of the page
        """
        self.driver.execute_script("window.scrollTo(0, 0)", "")
        self.wait(1, 1)

    def move_to_element2(self, xpath):
        """Moves to the element matching the xpath to make it interactable with

        Args:
            xpath (str): element xpath
        """
        ActionChains(self.driver).move_to_element(
            self.find_element_by_xpath(xpath)
        ).perform()

    def click_xpath2(self, xpath):
        """Moves to the element matching the xpath and wait before clicking on it

        Args:
            xpath (str): element xpath
        """
        self.move_to_element2(xpath)
        self.wait(1, 1)
        self.find_element_by_xpath(xpath).click()
        self.wait(1, 1)

    def choose_from_dropdown2(self, xpath, index=0, text=None, value=None):
        """Chooses an option from the dropdown matching the xpath. The option can be chosen by index, visible text or value. By defaut the first option is chosen.

        Args:
            xpath (str): dropdown xpath
            index (int, optional): index of the option. Defaults to 0.
            text (str, optional): text of the option. Defaults to None.
            value (int or str, optional): value of the option. Defaults to None.
        """
        self.move_to_element2(xpath)
        self.wait(1, 2)

        if value != None:
            Select(self.find_element_by_xpath(xpath)).select_by_value(str(value))
        elif text != None:
            Select(self.find_element_by_xpath(xpath)).select_by_visible_text(text)
        else:
            Select(self.find_element_by_xpath(xpath)).select_by_index(index)

    def back(self):
        self.driver.back()
