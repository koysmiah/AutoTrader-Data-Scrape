import os
import re
import time
import datetime

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

import psycopg2
from psycopg2 import sql
import csv
from sqlalchemy import create_engine

criteria = {
    "postcode": "LS1 2AD",
    "radius": "20",
    "year_from": "2010",
    "year_to": "2014",
    "price_from": "3000",
    "price_to": "6500",
}

cars = [
    {"make": "Toyota", "model": "Yaris"},
    {"make": "Honda", "model": "Jazz"},
    {"make": "Suzuki", "model": "Swift"},
    {"make": "Mazda", "model": "Mazda3"},
]

db_params = {
    'dbname': 'Autotrader',
    'user': 'postgres',
    'password': 'Compaq2022',
    'host': 'localhost',
    'port': '5432',
}

def scrape_autotrader(cars, criteria):
    chrome_options = Options()
    chrome_options.add_argument("_tt_enable_cookie=1")
    driver = webdriver.Chrome()
    data = []

    for car in cars:
        url = "https://www.autotrader.co.uk/car-search?" + \
            "advertising-location=at_cars&" + \
            "include-delivery-option=on&" + \
            f"make={car['make']}&" + \
            f"model={car['model']}&" + \
            f"postcode={criteria['postcode']}&" + \
            f"radius={criteria['radius']}&" + \
            "sort=relevance&" + \
            f"year-from={criteria['year_from']}&" + \
            f"year-to={criteria['year_to']}&" + \
            f"price-from={criteria['price_from']}&" + \
            f"price-to={criteria['price_to']}"

        driver.get(url)

        print(f"Searching for {car['make']} {car['model']}...")

        time.sleep(5)

        source = driver.page_source
        content = BeautifulSoup(source, "html.parser")

        try:
            number_of_pages = content.find("p", text=re.compile(r'Page \d{1,2} of \d{1,2}')).text[-1]
        except:
            print("No results found.")
            continue

        print(f"There are {number_of_pages} pages in total.")

        for i in range(int(number_of_pages)):
            driver.get(url + f"&page={str(i + 1)}")

            time.sleep(5)
            page_source = driver.page_source
            content = BeautifulSoup(page_source, "html.parser")

            articles = content.findAll("section", attrs={"data-testid": "trader-seller-listing"})

            print(f"Scraping page {str(i + 1)}...")

            for article in articles:
                details = {
                    "name": car['make'] + " " + car['model'],
                    "price": re.search("[£]\d+(\,\d{3})?", article.text).group(0),
                    "year": None,
                    "mileage": None,
                    "transmission": None,
                    "fuel": None,
                    "engine": None,
                    "owners": None,
                    "location": None,
                    "distance": None,
                    "link": article.find("a", {"href": re.compile(r'/car-details/')}).get("href")
                }

                try:
                    seller_info = article.find("p", attrs={"data-testid": "search-listing-seller"}).text
                    location = seller_info.split("Dealer location")[1]
                    details["location"] = location.split("(")[0]
                    details["distance"] = location.split("(")[1].replace(" mile)", "").replace(" miles)", "")
                except:
                    print("Seller information not found.")

                specs_list = article.find("ul", attrs={"data-testid": "search-listing-specs"})
                for spec in specs_list:
                    if "reg" in spec.text:
                        details["year"] = spec.text

                    if "miles" in spec.text:
                        details["mileage"] = spec.text

                    if spec.text in ["Manual", "Automatic"]:
                        details["transmission"] = spec.text

                    if "." in spec.text and "L" in spec.text:
                        details["engine"] = spec.text

                    if spec.text in ["Petrol", "Diesel"]:
                        details["fuel"] = spec.text

                    if "owner" in spec.text:
                        details["owners"] = spec.text[0]

                data.append(details)

            print(f"Page {str(i + 1)} scraped. ({len(articles)} articles)")
            time.sleep(5)

        print("\n\n")

    print(f"{len(data)} cars total found.")

    # Convert the list of dictionaries to a pandas DataFrame
    df = pd.DataFrame(data)

    return df

# Upload to PostGreSQL
engine = create_engine('postgresql://{user}:{password}@{host}:{port}/{dbname}'.format(**db_params))
table_name = 'Autotrader_Data'
data_df.to_sql(table_name, engine, if_exists='replace', index=False)

