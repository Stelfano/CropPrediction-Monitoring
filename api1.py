import requests
import time
import json

counter = 1
product_counter = 0
year_counter = 0
product = 'fruitAndVegetable'
marketYear = ['2010', '2011', '2012', '2013', '2014', '2015' ,'2016', '2017', '2018', '2019', '2020', '2021', '2022']

while year_counter < len(marketYear):
    #Per il momento funziona solo per il 2016 aggiungere metodo per cambiare l'anno
    request_string = "https://www.ec.europa.eu/agrifood/api/{product}/prices?calendarYears={year}&weeks={weeknum}&products=apples"
    final_request = request_string.format(product=product, year=marketYear[year_counter], weeknum=counter)
    print(final_request)
    dump_filename = "Data/dump1.json"

    response = requests.get(final_request)
    print(response.status_code)

    with open(dump_filename, "a") as file:
        json.dump(response.json(), file)
        file.write("\n")


    counter += 1
    
    if counter % 52 == 0:
        year_counter += 1
        counter = 1
    
