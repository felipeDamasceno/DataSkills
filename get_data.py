""" This script extracts brasilians data science and data analyst jobs description, title and location from indeed.

Everything is stored in my local MySQL database and the title is used to find the job position (analista de dados or cientista de dados).
"""

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains

import sqlalchemy as db

from datetime import datetime, timedelta
import pandas as pd
import random
import time
import yaml
import csv
import re

def sleep(seconds=None):
    """ Pause the execution for the seconds specified in the parameter or 2 to 8 seconds otherwise.
    """
    if not seconds:
        seconds = random.randrange(2,8)
    time.sleep(seconds)
    
def skip_line_cleaning(x):
    """ Remove skip line and multiple spaces from text
    """
    x = re.sub("\.\s?\n+", ". ", x)
    x = re.sub(":\s?\n+", ": ", x)
    x = re.sub(";\s?\n+", "; ", x)
    x = re.sub("\n+", ". ", x)
    x = re.sub("\s+", " ", x)
    return x
                
        
def get_job_title(driver):
    """ Find and extract the job title information in the indeed job page.
    """
    try:
        position = driver.find_element('xpath',
                                       "/html/body/div[2]/div[2]/div/div[4]/div/div/div[1]/div[1]"\
                                       "/div[2]/div[1]/div[1]/h1/span").text
        
        return position
    except NoSuchElementException:
        return None
    
def get_company_location(driver):
    """ Find and extract the job location information in the indeed job page.
    """
    try:
        location = driver.find_element('xpath',
                                      "/html/body/div[2]/div[2]/div/div[4]/div/div/div[1]/div[1]/div[2]"\
                                      "/div[1]/div[2]/div/div/div/div[2]/div").text
        return location
    except NoSuchElementException:
        return None
    
def get_job_description(driver):
    """ Find and extract the job description information in the indeed job page.
    """
    try:
        description = driver.find_element('xpath',
                                      '//*[@id="jobDescriptionText"]').text
        
        return skip_line_cleaning(description)
    except NoSuchElementException:
        return None
    

def title_to_position(title):
    """ Check if the job title has some keywords for the jobs Data Science and Data Analyst and return one of the
    two jobs or "no position" otherwise.
    """
    title = title.lower()
    if (("cientista" in title) and ("dado" in title)) or (("scientist" in title) and ("data" in title)):
        return "Cientista de Dados"
    elif ("analista de dados" in title) or (("analyst" in title) and ("data" in title)):
        return "Analista de Dados"
    else:
        return None
    
def get_job_links(driver, n_pages, current_links):
    """ Get the links where the job description is located.
    
    Parameters:
    - driver: Selenium page of the job searched
    - n_pages: Number of times to go to the next page to get more job links
    - current_links: Links we already have extracted
    
    Return:
    - List of the job links
    """
    links = []
    wait = WebDriverWait(driver, 30)
    for i in range(n_pages):
        try:
            new_links = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "jcs-JobTitle")))
            links.extend([l.get_attribute("href") for l in new_links if l.get_attribute("href") not in links])
            
            print("Current page number:", i)
            print("Quantidade de Links:", len(links))

        
            next_pages = wait.until(EC.presence_of_all_elements_located((By.XPATH, 
                                                                        "/html/body/main/div/div[1]/div/div/div[5]/"\
                                                                        "div[1]/nav/div[6]/a")))
                                                                       
            driver.get(next_pages[0].get_attribute("href"))
            sleep()
        except Exception as e:
            print("Próxima página não encontrada")
            print("Quantidade de Links:", len(links))
            break
            
    return [l for l in links if l not in current_links]
    
def loop_job_links(driver, url, keywords, n_pages, current_links):
    """ Search for the keywords and get the job links from the search result.
    
    Parameters:
    - driver: Selenium page of the job searched
    - url: Site to scrapy, indeed web site
    - keywords: List of the jobs to search
    - n_pages: Number of times to go to the next page to get more job links for each keyword
    - current_links: Links we already have extracted
    
    Return:
    - List of the job links
    """
    all_links = []
    for keyword in keywords:
    
        driver.get(url)
        driver.current_url
        
        print("Procurando por:", keyword)

        #searching in a bar
        search_bar = driver.find_element('name',"q")
        search_bar.clear()
        search_bar.send_keys(keyword)
        search_bar.send_keys(Keys.RETURN)

        driver.current_url
        
        links = get_job_links(driver, n_pages=n_pages, current_links=current_links)
        all_links.extend(links)
        current_links.extend(links)
        
    return all_links

def engine_db():
    """ Return engine of MySQL DB to connect to the DB.
    """
    credentials = yaml.full_load(open('./credentials.yml'))
    user = credentials['database']['username']
    password = credentials['database']['password']
    host = credentials['database']['hostname']
    database = 'indeed_jobs'

    string_conexao = f'mysql://{user}:{password}@{host}/{database}'
    engine = db.create_engine(string_conexao)
    
    return engine

# Connect to the MySQL DB
engine = engine_db()
conn = engine.connect()

# Get the job_description table
metadata = db.MetaData()
job = db.Table('job_descriptions', metadata, autoload_with=engine)

#setting driver
options = webdriver.ChromeOptions()
options.add_argument("--incognito")
options.add_argument('--disable-gpu')

############# CONFIGURATION #############################
#type the job titles you are looking for
keywords = ["cientista de dados", "analista de dados"]

#url of site we are scapping
url = "https://br.indeed.com"

# Number of times to go to the next page to get more job links for each search in the indeed site.
n_pages = 15
##########################################################
driver = webdriver.Chrome(options=options)

# Get links scraped from DB
query = db.select(job.columns.indeed_link)
results = conn.execute(query).fetchall()
current_links = [r[0] for r in results]

links = loop_job_links(driver, url, keywords, n_pages=n_pages, current_links=current_links)

print("Scraping links")

for l in links:
    
    sleep()
    driver.get(l)
    sleep()
    
    title = get_job_title(driver)
    
    if title != None:
        position = title_to_position(title)
    else:
        position = None
    
    if position != None:

        location = get_company_location(driver)    

        description = get_job_description(driver)

        # Saving in MySQL
        try:
            stmt = db.insert(job).values(indeed_link=l, location=location, description=description, 
                                         indeed_title=title, position=position)

            conn.execute(stmt) 
            conn.commit()    
        except Exception as e:        
            print(f"Não foi possível inserir o regristro {l}. O erro foi encontrado foi: {e}") 

print("Informação extraída com sucesso!")