from distutils.log import debug
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from datetime import date
import pandas as pd

import time
import datetime
import requests

BASE_URL = "https://www.albconnect.com.au/storefront/sga/en/AUD"

data = open("config.txt", "r")
for x in data:
    if 'download_path' in x:
        download_path = x.replace('download_path = ', '').replace('\n', '')
    if 'username' in x:
        username = x.replace('username = ', '').replace('\n', '')
    if 'password' in x:
        password = x.replace('password = ', '').replace('\n', '')
    if 'start_date' in x:
        start_date = x.replace('start_date = ', '').replace('\n', '')
    if 'end_date' in x:
        end_date = x.replace('end_date = ', '').replace('\n', '')

def getDates():
    today = datetime.date.today()

    if today.month == 1:
        last_month = today.replace(month=12)
        last_month = last_month.replace(year=today.year - 1)

    else:
        last_month = today.replace(day=1)
        last_month = last_month.replace(month=last_month.month - 1)
        last_month = last_month.strftime("%d/%m/%Y")
        today = today.strftime("%d/%m/%Y")

    return last_month, today


def getOrderInfo(page):
    global counter
    global items

    body = page.query_selector("body")
    soup = BeautifulSoup(body.inner_html(), 'html.parser')

    orderNo = soup.find('div', {'class': 'account-section-header'}).find('span').text.replace('Order:', '').strip()

    itemLabels = soup.find_all('span', {'class': 'item-label'})
    status = itemLabels[0].text.replace('Status:', '').strip()
    datePlaced = itemLabels[1].text.replace('Date Placed:', '').strip()
    orderType = itemLabels[2].text.replace('Type:', '').strip()

    valueTitleDivs = soup.find_all('div', {'class': 'value-title'})
    paymentMethod = valueTitleDivs[0].text.replace('Payment Method:', '').strip()
    deliveryDate = soup.find('div', {'class': 'order-history-defered-date'}).text

    products = soup.find('div', {'class', 'storefront_table'})

    if (products):

        products = products.find_all('li', {'class', 'item__list--item'})
        print(len(products))
        for product in products:
            productInfo = product.find_all('div', {'class': 'order-history-table-val'})
            productNo = productInfo[0].find('div', {'class': 'sga-product-code'}).text.strip()
            productName = productInfo[0].text.strip().replace(productNo, '').replace('\n', '').replace('  ', '').strip()
            itemPrice = productInfo[1].text.replace('Item price:', '').replace('\n', '').replace('  ', '').strip()
            itemStatus = productInfo[2].find('span', {'class': 'qtyValue'}).text.replace('\n', '').strip()
            itemQuantity = productInfo[3].find('span', {'class': 'qtyValue'}).text.replace('\n', '').strip()
            invoicedQuantity = productInfo[4].find('span', {'class': 'qtyValue'})
            if invoicedQuantity:
                invoicedQuantity = invoicedQuantity.text.replace('\n', '').strip()
            totalAmount = productInfo[5].text.replace('Total:', '').replace('\n', '').strip()
            # print(productNo)
            # print(productName)
            # print(itemPrice)
            # print(itemStatus)
            # print(itemQuantity)
            # print(invoicedQuantity)
            # print(totalAmount)

            print(counter, orderNo, status, datePlaced, orderType, paymentMethod, deliveryDate, productNo, productName,
                  itemPrice, itemStatus, itemQuantity, invoicedQuantity, totalAmount)

            items[counter] = [counter, orderNo, status, datePlaced, orderType, paymentMethod, deliveryDate, productNo,
                              productName, itemPrice, itemStatus, itemQuantity, invoicedQuantity, totalAmount]
            counter += 1


def login(page, context):
    time.sleep(3)
    if page.url == BASE_URL + "/login":
        print('Logging in ...')
        page.fill('input#j_username', username)
        page.fill('input#j_password', password)
        page.get_by_role("button", name="Log In").click()
        context.storage_state(path="auth.json")
    else:
        print('Already logged in ...')


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context(storage_state="auth.json")
    page = context.new_page()

    page.goto(BASE_URL + '/my-account/orders')

    login(page, context)
    time.sleep(2)

    last_month, today = getDates()
    if 'start_date' not in locals():
        start_date = last_month
    if 'end_date' not in locals():
        end_date = today

    orderPages = []

    for x in range(50):
        page.goto(BASE_URL + '/my-account/orders?startDate=' + start_date + '&endDate=' + end_date + '&page=' + str(x))
        time.sleep(5)

        table = page.query_selector("tbody")
        tableRows = BeautifulSoup(table.inner_html(), 'html.parser')

        if (tableRows.find_all('tr')):
            for row in tableRows.find_all('tr'):
                link = row.find_all('td')
                link = link[1].find('a')['href']
                link = 'https://www.albconnect.com.au' + link
                orderPages.append(link)
        else:
            break

    print(orderPages)

    counter = 1
    items = {}

    for orderpage in orderPages:
        print(orderpage)
        page.goto(orderpage)
        time.sleep(2)

        getOrderInfo(page)

        print("____________________________________________________________________________________________")

    productsOrders = pd.DataFrame.from_dict(items, orient='index',
                                            columns=["Counter", "Order No", "Status", "Date Placed", "Order Type",
                                                     "Payment Method", "Delivery Date", "Product No", "Product Name",
                                                     "Item Price", "Item Status", "Item Quantity", "Invoiced Quantity",
                                                     "Total Amount"])
    productsOrders.to_csv(download_path + "/" + str(time.time()) + ".csv", sep='|', index=False)

print('Completed')
