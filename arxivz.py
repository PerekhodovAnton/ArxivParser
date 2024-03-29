import requests
import re 
import os 
import math
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup as bs
import matplotlib.pyplot as plt
import urllib3
import wget
import PyPDF2
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) 

class Arxiv:
    _articles_per_page = 200

    def __page_parse(url):
        response = requests.get(url, verify=False)

        if response.status_code == 200: 
            html_content = response.content
            soup = bs(html_content, 'html.parser')
            titles = soup.find_all('p', class_='title is-5 mathjax')
            titles = [' '.join(re.findall(r'[^ ]{2,}', title.text.replace('\n', ''))) for title in titles]
            links = soup.find_all('a')
            links_to_download = [i.replace('"', '') for i in re.findall('https://arxiv.org/pdf/.*?"', str(links))]

            return titles, links_to_download
        
        else:
                        
            return f'ERROR: {response.status_code}'
    
    @classmethod
    def make_parse(cls, from_date: str, to_date: str, key_words: list) -> dict:
        key_words_and_count = {}
        titles_with_links = {}

        for key_word in key_words:

            arxiv_url = f'https://arxiv.org/search/advanced?advanced=&terms-0-operator=AND&terms-0-term={key_word}\
                        &terms-0-field=all&classification-physics_archives=all&classification-include_cross_list=include&date-year\
                        =&date-filter_by=date_range&date-from_date={from_date}&date-to_date={to_date}&date-date_type=submitted_date&\
                        abstracts=show&size={cls._articles_per_page}&order=-announced_date_first'
            
            response = requests.get(arxiv_url, verify=False)

            if response.status_code == 200:
                html_content = response.content
                soup = bs(html_content, 'html.parser')
                count = soup.find_all('h1', class_='title is-clearfix')

                if re.findall(r'Sorry', str(count)):
                    counts = '0'

                else:
                    counts = re.findall(r'[0-9]?,?[0-9]+ results', str(count))[0].replace('results', '').replace(',', '')
                    authors = soup.find_all('p', class_='authors')
                    authors = [a.replace('">', '').replace('</a>', '').replace(' ', '+') for a in re.findall(r'">.*?</a>', str(authors))]
                
                titles, links_to_download = cls.__page_parse(arxiv_url)

                for t, l in zip(titles, links_to_download):
                        if t not in titles_with_links:
                            titles_with_links[t] = l

                for page in range(int(math.ceil(int(counts)/200))-1):
                    arxiv_page = f'{arxiv_url}&start={(page+1)*cls._articles_per_page}'
                    titles, links_to_download = cls.__page_parse(arxiv_page)

                    for t, l in zip(titles, links_to_download):
                        if t not in titles_with_links:
                            titles_with_links[t] = l
                    

                key_words_and_count[key_word] = int(counts.replace(' ', ''))
            
            else:
                return f'ERROR: {str(requests.get(arxiv_url, verify=False))}'
            
        return titles_with_links, key_words_and_count

    @classmethod
    def make_parse_2periods_and_draw_graph(cls, past_from_date: str, past_to_date: str, now_from_date: str, now_to_date: str, key_words: list) -> plt:
        data_was = cls.make_parse(past_from_date, past_to_date, key_words)[1]
        data_became = cls.make_parse(now_from_date, now_to_date, key_words)[1]
        merged_data = {}

        for key, value in data_was.items():
            merged_data.setdefault(key, []).append(value)

        for key, value in data_became.items():
            merged_data.setdefault(key, []).append(value)

        categories = list(data_was.keys())
        values_was = list(map(int, [i[0] for i in merged_data.values()]))
        values_became = list(map(int, [i[1] for i in merged_data.values()]))
        index = np.arange(len(categories))
        bar_height = 0.35

        with plt.style.context('dark_background'):
            plt.bar(index, values_was, width=bar_height, color='orange', label='Было')
            plt.bar(index + bar_height, values_became, width=bar_height, color='green', label='Стало')
            plt.ylabel('Количество')
            plt.xlabel('Категории')
            plt.title('Сравнение "было" и "стало"')
            plt.xticks(index + bar_height/2, categories, rotation=70)
            plt.legend()

        return plt.show()

    @classmethod            
    def get_links(cls, now_from_date: str, now_to_date: str, key_words: list) -> list:
        return [i for i in cls.make_parse(now_from_date, now_to_date, key_words)[0].values()]
    
    @classmethod 
    def save_pdfs_and_get_pages(cls, now_from_date: str, now_to_date: str, path_to_save: str, key_words: list) -> list:
        links = cls.get_links(now_from_date, now_to_date, key_words)
        not_downloaded = []

        for url in links:
            try:
                wget.download(url + '.pdf', path_to_save)

            except:
                print(f'{url}.pdf is not downloaded')
                not_downloaded.append(url + '.pdf')
                pass

        return not_downloaded
    
    @classmethod
    def count_pages(cls, path_to_files: str) -> int:
        files = os.listdir(path_to_files)
        page_count = 0
        for file in files:
            file = open(path_to_files + '\\' + file, 'rb') 
            pdfReader = PyPDF2.PdfReader(file) 
            page_count += len(pdfReader.pages)

        return page_count

