import logging
import os
import re
from datetime import date, datetime
from itertools import product

import numpy as np
import pandas as pd
import yaml

# from app.config import is_dev
from scraping_class import ScrapingClass
from selenium.webdriver.common.by import By

from concurrent.futures import ThreadPoolExecutor
import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

HERE = os.path.realpath(os.path.dirname(__file__))


def gas_category(gas_consumption):
    if gas_consumption < 1000:
        category = "Base"
    elif 1000 <= gas_consumption < 6000:
        category = "B0"
    elif 6000 <= gas_consumption < 30000:
        category = "B1"
    elif 30000 <= gas_consumption < 150000:
        category = "B2i"
    return category

def gas_zone(zip_code):
    if zip_code == 13008:
        gas_zone = 1
    elif zip_code == 75008:
        gas_zone = 2
    elif zip_code == 66000:
        gas_zone = 3
    elif zip_code == 24200:
        gas_zone = 4
    elif zip_code == 73200:
        gas_zone = 5
    elif zip_code == 22560:
        gas_zone = 6
    return gas_zone

# Collect cookies
def get_cookies(driver):
    cookies = {}
    for cookie in driver.get_cookies():
        cookies.update({cookie['name']:cookie['value']})
    return cookies

# Retrieve token
def get_token_search(html):
    soup = BeautifulSoup(html, 'html.parser')
    token_elmt = soup.find(id='offer_filters__token')
    token_filter = token_elmt.get('value')
    return token_filter

class ScrapingEnergieInfo:
    def __init__(self):

        with open(
            os.path.join(
                HERE,
                # f"config_files/settings_mediateurenergie{'_dev' if is_dev() else ''}.yaml",
                f"config_files/settings_mediateurenergie_dev.yaml",
            ),
            "r",
        ) as ymlfile:
            self.settings = yaml.safe_load(ymlfile)

        self.today = str(datetime.today().date())
        self.sc = ScrapingClass()  # config["driver_path"]
        self.url = self.settings["url"]

        self.options_profile = self.settings["options"]["profile"]
        self.options_energy_type = self.settings["options"]["energy type"]
        self.options_elec_consumption_type = self.settings["options"]["elec consumption type"]
        self.options_elec_zip_code = self.settings["options"]["zip code"]["elec"]
        self.options_gas_zip_code = self.settings["options"]["zip code"]["gas"]
        self.options_counter_power = self.settings["options"]["counter power"]
        self.options_gas_consumption = self.settings["options"]["gas consumption"]

        self.current_option = None
        self.raw_offers = []
        self.start = datetime.now()

        self.headers = {
            'accept': '*/*',
            'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'priority': 'u=1, i',
            'referer': 'https://comparateur-offres.energie-info.fr/',
            'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
            }

    def log_duration(self, desc:str = 'Time'):
        duration = str(datetime.now() - self.start)
        log.info(' : '.join([desc,duration]))

    def remove_forbidden_options(self, options:list):
        """
        Remove options that doesn"t exist / can't be scraped. Only for elec peak/offpeak - 3kva for now
        """
        to_remove = []
        forbidden_options = self.settings["options"]["forbidden"][self.energy_type]
        
        for forbidden in forbidden_options:
            for option in options:
                if all([option[ind] == forbidden[ind] for ind in range(len(forbidden))]):
                    to_remove.append(option)

        [options.remove(option) for option in to_remove]
        
        return options
    
    def set_profile_options(self, profile, energy_type):
        self.profile = profile
        self.energy_type = energy_type
        
        if self.energy_type == "elec":
            options = list(
                product(
            self.options_elec_consumption_type,
            self.options_counter_power,
            self.options_elec_zip_code,
            )
            )
        elif energy_type == "gas":
            options = list(
                product(self.options_gas_consumption, self.options_gas_zip_code)
            )
        
        self.options = self.remove_forbidden_options(options)
    
    def run_options(self):
        
        for ind, option in enumerate(self.options, start = 1):
            log.info(f"option [{ind:02d}/{len(self.options):02d}] - {option}")
            if self.energy_type == 'elec':
                self.current_option = option
                self.elec_consumption_type = option[0]
                self.counter_power = option[1]
                self.zip_code = option[2]

            elif self.energy_type == 'gas':
                self.current_option = option
                self.gas_consumption = option[0]
                self.zip_code = option[1]

            self.main_run()
            self.log_duration(desc=f'Duration after option {ind:02d}')

    def scrap_comparateur_offre(self, profile, energy_type):
        """
        Running function
        """
        log.info(f'Scraping profile : {profile} - energy_type : {energy_type}')
        self.set_profile_options(profile, energy_type)
        self.sc.get(self.url)
        self.choose_private_pro()
        self.run_options()
        self.cleaning_result(energy_type=energy_type)
        self.log_duration(desc='Total time')
        self.sc.quit()
        return self.all_offers

    def choose_private_pro(self):
        """
        Change the profile of the user (private/professional)
        """
        if self.profile == "professional":
            self.click_cookies(self.sc.driver)
            sliders = self.sc.find_elements_by_xpath(self.settings["xpath"]["profile slider"])
            for el in sliders:
                try:
                    el.click()
                    break
                except:
                    continue
            
            self.sc.click_css_selector(
                self.settings["selector"]["profile reset button"]
            )
        else:
            pass
        
    def click_cookies(self, driver):
        try:
            cookie_el_list = driver.find_elements(By.XPATH, value=self.settings["xpath"]["cookie banner"])
            if cookie_el_list:
                cookie_el_list[0].click()
        except Exception as e:
                log.info(f"Exception clicking cookies")
                pass
        
    def first_page(self):
        """
        Goes through the first page of the website selecting options from settings file
        """
        self.click_cookies(self.sc.driver)
        self.sc.send_xpath(self.settings["xpath"]["zip code"], self.zip_code)
        self.sc.wait(1, 2)
        self.sc.click_xpath(self.settings["xpath"]["city"])
        self.sc.click_xpath(self.settings["xpath"]["energy type"][self.energy_type])

        self.sc.click_xpath(self.settings["xpath"]["next button"])

    def second_page(self):
        """
        Goes through the second page of the website selecting options from settings file
        """
        if self.energy_type == "elec":
            self.sc.click_xpath(self.settings["xpath"]["linky counter"])
            for elmt in ['has contract', 'know prm']:
                try:
                    self.sc.click_xpath(self.settings["xpath"][elmt])
                except:
                    log.info(f'element not found page 2: {elmt}')

            if self.profile == "private":
                self.sc.click_xpath(
                    self.settings["xpath"]["elec consumption knowPower"]
                )
            self.sc.click_xpath(
                "//select[@id='elec_consumption_power']//option[normalize-space()='"
                + str(self.counter_power)
                + " kVA']"
            )
            self.sc.click_xpath(
                self.settings["xpath"]["elec consumption type"][
                    self.elec_consumption_type
                ]
            )
            self.sc.click_xpath(self.settings["xpath"]["elec consumption knowConso"])
        elif self.energy_type == "gas":
            self.sc.click_xpath(self.settings["xpath"]["gas consumption knowPower"])
            self.sc.send_xpath(
                self.settings["xpath"]["gas consumption"], self.gas_consumption
            )
            self.sc.click_keyboard_enter()

        self.sc.click_css_selector(self.settings["selector"]["submit button"])

    def third_page(self):
        """
        Goes through the third page of the website selecting options from settings file
        """
        self.sc.click_xpath(self.settings["xpath"]["sorted by provider"])
        if self.profile == "professional":
            self.sc.click_xpath(self.settings["xpath"]["displayed price"])
        self.sc.click_css_selector(self.settings["selector"]["submit button"])

    def processing_prices(self, price_string):
        """
        Transforms the string giving the price by extracting the numbers and calculating the matching price
        """
        price = re.search(self.settings["regexp"]["re_price"], price_string)
        if price is None:
            return price_string
        else:
            return float((
                price.groupdict().get('price').replace(",", ".")
                if price.groupdict().get('price')
                else 0
                ))

    def processing_consumption_type(self, string, consumption_type = None):
        """
        Transforms the string giving the consumption type & price by extracting the numbers and calculating the matching date.
        Return : Array of float prices depending on price type:
        - elec consumption price : [conso_ht, conso_ttc, hc_ht, hc_ttc, hp_ht, hp_ttc]
        - gas consumption price : [conso_ht, conso_ttc]
        - subscription price : [sub_ht, sub_ttc]
        """
        matchs_dict = {}
        if consumption_type and consumption_type != 'gas':
            if consumption_type == 'peak/offpeak':
                for hour_type in ['peak', 'offpeak']:
                    price_string = re.search(self.settings["regexp"][f"re_{hour_type}"], string.lower())
                    matchs_dict.update(price_string.groupdict())

            elif consumption_type == 'base':
                price_string = re.search(self.settings["regexp"][f"re_base"], string.lower())
                matchs_dict.update(price_string.groupdict())

            prices = {price_type:self.processing_prices(price) for price_type, price in matchs_dict.items()}
            
            return [
                prices.get('conso_ht'),
                prices.get('conso_ttc'),
                prices.get('hc_ht'),
                prices.get('hc_ttc'), 
                prices.get('hp_ht'),
                prices.get('hp_ttc'),
                ]
        
        elif consumption_type == 'gas':
            price_string = re.search(self.settings["regexp"][f"re_gas"], string.lower())
            matchs_dict.update(price_string.groupdict())
            prices = {price_type:self.processing_prices(price) for price_type, price in matchs_dict.items()}
            return [
                prices.get('conso_ht'),
                prices.get('conso_ttc'),
                ]
            
        else: # subscription price
            price_string = re.search(self.settings["regexp"][f"re_subscription"], string.lower())
            matchs_dict.update(price_string.groupdict())
            prices = {price_type:self.processing_prices(price) for price_type, price in matchs_dict.items()}
            return [
                prices.get('sub_ht'), 
                prices.get('sub_ttc'), 
                ]

    def processing_dates(self, date_string):
        """
        Transforms the string giving the date by extracting the numbers and calculating the matching date
        """
        date = re.search(self.settings["regexp"]["re_date"], date_string)
        if date is None:
            return date
        else:
            return datetime.strptime(str(date.group(0)), "%d/%m/%Y")

    def processing_power(self, counter_string):
        """
        Transforms the string giving the counter power by extracting the numbers and calculating the matching date
        """
        counter = re.search(self.settings["regexp"]["re_power"], counter_string)
        if counter is None:
            return counter_string
        else:
            return counter.group(0)

    def additional_columns(self, df, energy_type):
        """
        Clean columns by splitting prices and converting dates
        """
        df['offer_name'] = df.apply(
            lambda row: (
                row["offer"].split("\n")[0] if pd.notnull(row["offer"]) else None
            ),
            axis=1,
        )
        
        if energy_type == 'elec':
            df['counter_power'] = df.apply(
                lambda row: (
                    self.processing_power(row["counter_power"])
                    if pd.notnull(row["counter_power"])
                    else None
                ),
                axis=1,
            )
            df[[
                'consumption_price_ht', 
                'consumption_price_ttc', 
                'hc_consumption_price_ht', 
                'hc_consumption_price_ttc',
                'hp_consumption_price_ht', 
                'hp_consumption_price_ttc'
                ]] = df.apply(lambda row: 
                              self.processing_consumption_type(string=row['kwh_price'], consumption_type=row['consumption_type']),
                              axis = 1,
                              result_type ='expand'
                              )

        elif energy_type == 'gas':
            df[['consumption_price_ht',
               'consumption_price_ttc',
               ]] = df.apply(lambda row:
                             self.processing_consumption_type(string=row['kwh_price'], consumption_type='gas'),
                             axis = 1,
                             result_type ='expand'
                             )
        

        df[['subscription_price_ht',
           'subscription_price_ttc'
           ]] = df.apply(lambda row: 
                         self.processing_consumption_type(string=row['subscription_price']),
                         axis = 1,
                         result_type ='expand'
                         )

        df["begin_validity_date"] = pd.to_datetime(
            df.apply(lambda row: (self.processing_dates(row["begin_date"])), axis=1)
        ).dt.date
        df["end_validity_date"] = pd.to_datetime(
            df.apply(lambda row: (self.processing_dates(row["end_date"])), axis=1)
        ).dt.date
        df["last_updated_date"] = pd.to_datetime(
            df.apply(
                lambda row: (self.processing_dates(str(row["updated_date"]))), axis=1
            )
        ).dt.date

        df = df.drop(columns=['begin_date', 'end_date','updated_date'])

        df["scraping_date"] = date.today()

        return df

    def cleaning_result(self, energy_type):
        """
        Create the final table that will be uploaded into BigQuery
        """
        
        self.all_offers = pd.DataFrame().from_records(self.raw_offers)

        self.all_offers.rename(columns=self.settings["results"]["rename"], inplace=True)
        self.all_offers = self.additional_columns(df=self.all_offers, energy_type=energy_type)
        self.all_offers = self.all_offers.loc[:, ~self.all_offers.columns.duplicated()]

        # Filter columns specific to elec when scraping gas (and reverse)
        ordered_columns = [col for col in self.settings["results"]["ordered_columns"] if col in self.all_offers.columns]

        self.all_offers = self.all_offers[ordered_columns]

        if energy_type == 'gas':
            try:
                self.all_offers["gas_zone"] = self.all_offers["gas_zone"].fillna(value=np.nan).astype("int64")
                # self.all_offers["gas_zone"] = self.all_offers["gas_zone"].astype("int64")
            except:
                pass
        
        elif energy_type == 'elec':
            self.all_offers["hp_consumption_price_ht"] = self.all_offers[
                "hp_consumption_price_ht"
            ].astype("float64")
            self.all_offers["hp_consumption_price_ttc"] = self.all_offers[
                "hp_consumption_price_ttc"
            ].astype("float64")
            self.all_offers["hc_consumption_price_ht"] = self.all_offers[
                "hc_consumption_price_ht"
            ].astype("float64")
            self.all_offers["hc_consumption_price_ttc"] = self.all_offers[
                "hc_consumption_price_ttc"
            ].astype("float64")
            self.all_offers["subscription_price_ht"] = self.all_offers[
                "subscription_price_ht"
            ].astype("float64")
            self.all_offers["subscription_price_ttc"] = self.all_offers[
                "subscription_price_ttc"
            ].astype("float64")

        for date_col in self.all_offers.columns:
            if 'date' in date_col:
                self.all_offers[date_col] = self.all_offers[date_col].astype(str)
  
    def get_offer_ids_providers(self,driver):
        # Get offer ids
        cookies = get_cookies(driver)
        token_filter = get_token_search(driver.page_source)
        last = False
        ind = 1

        offers_ids_providers = []

        params = {
            's': '',
            'offer_filters[fullGreen]': '0',
            'offer_filters[fullOnLine]': '0',
            'offer_filters[period]': '12',
            'offer_filters[linky]': '0',
            'offer_filters[sortBy]': '3',
            'offer_filters[sortDirection]': 'ASC',
            'offer_filters[_token]': token_filter,
        }

        while last is False:
            url_filtered_results = f'https://comparateur-offres.energie-info.fr/results/{ind}'
            response = requests.get(url_filtered_results, params=params, cookies=cookies, headers=self.headers)
            
            soup_test = BeautifulSoup(response.json().get('html'), 'html.parser')
            offers = soup_test.find_all('div', class_ ='offre offer')
            for el in offers:
                offer_id = el.get('data-id')
                url_provider = f'https://api-comparateur-offres.energie-info.fr/api/files/offers/{offer_id}/logo'
                provider = el.find('img', {'src':url_provider}).get('alt')
                offers_ids_providers.append({'id':offer_id, 'provider': provider})
            
            if response.json().get('lastPage'):
                last = True

            ind+=1

        log.info(f'offers : {len(offers_ids_providers)}')
        return offers_ids_providers
    
    def add_offer_details_threaded(self, driver, offers_records):
        # Update cookies
        cookies = get_cookies(driver)
        url_detail = 'https://comparateur-offres.energie-info.fr/detail/'

        def fetch_details(el):
            url_id = url_detail + el.get('id')
            res = requests.get(url=url_id, cookies=cookies, headers=self.headers)
            el.update({'soup': BeautifulSoup(res.content, 'html.parser')})

        with ThreadPoolExecutor() as executor:
            list(executor.map(fetch_details, offers_records))
    
    def get_offer_from_rows(self, result_rows, offer):
        for row in result_rows:
        ## Add additionnal keys from rows in result based on yaml settings for results columns
            children = row.children

            if any([child.name == "td" for child in children]): # Filter rows that have no values
                
                key = row.find('th').get_text(strip = True)
                if key == 'Offre':
                    value = row.find('td').find('h5').get_text(strip = True)    
                else:
                    value = row.find('td').get_text(strip = True)

                if key in self.settings['results']['columns']: # Only keeps desired columns
                    offer[key] = value
        return offer    
    
    def get_distributor(self, soup):
        for tag in soup.find_all('h4'):
            if tag.get_text(strip=True) and re.search('distributeur', tag.get_text(strip=True), re.IGNORECASE):
                return tag.get_text().split('\n')[1].split(':')[-1].strip()
    
    def get_raw_offers_elec(self, offers_records):
        offers = []
        for offer_dict in offers_records:
            offer = {
                'offer_id' : offer_dict.get('id'),
                'provider_name' : offer_dict.get('provider'),
                'distributor_name' : self.get_distributor(offer_dict.get('soup')),
                'profile' : self.profile,
                'energy_type' : self.energy_type,
                'consumption_type' : self.elec_consumption_type,
                }
            result_rows = offer_dict.get('soup').find(id = 'electricite').find_all('tr')        
            offer = self.get_offer_from_rows(result_rows, offer)
            offers.append(offer)

        return offers
    
    def get_raw_offers_gas(self, offers_records):
        offers = []
        for offer_dict in offers_records:
            offer = {
                'offer_id' : offer_dict.get('id'),
                'provider_name' : offer_dict.get('provider'),
                'distributor_name' : self.get_distributor(offer_dict.get('soup')),
                'profile' : self.profile,
                'energy_type' : self.energy_type,
                'gas_category' : gas_category(self.gas_consumption),
                'gas_zone' : gas_zone(self.zip_code),
                }
            result_rows = offer_dict['soup'].find(id = 'gaz').find_all('tr')        
            offer = self.get_offer_from_rows(result_rows, offer)
            offers.append(offer)

        return offers

    def scroll_up_while_possible(self):
        """
        To avoid a TimeOut Exception and try several times to scroll up
        """
        for i in range(15):
            try:
                self.sc.scroll_up()
                self.sc.wait(4, 5)
                break
            except:
                continue
                     
    def new_simulation(self):
        """
        Launch a new simulation
        """
        try:
            # self.sc.wait(4, 5)
            self.scroll_up_while_possible()
            self.sc.wait_until_click_selector(
                self.settings["selector"]["new simulation"]
            )
            self.sc.wait(1, 2)
            self.sc.click_css_selector(
                self.settings["selector"]["new simulation confirmation"]
            )
        except:
            self.sc.get(self.url)

    def main_run(self):
        """
        Main running function for a unique combination of options
        """

        self.first_page()
        self.second_page()
        self.third_page()

        self.offers_records = self.get_offer_ids_providers(driver=self.sc.driver)
        # update offers_records with soup
        self.add_offer_details_threaded(driver=self.sc.driver, offers_records=self.offers_records)
        
        if self.energy_type == 'elec':
            self.raw_offers.extend(self.get_raw_offers_elec(offers_records=self.offers_records))
        elif self.energy_type == 'gas':
            self.raw_offers.extend(self.get_raw_offers_gas(offers_records=self.offers_records))
        
        self.new_simulation()
