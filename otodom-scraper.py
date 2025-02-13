import streamlit as st
import datetime
import pandas as pd
import io
import requests
from bs4 import BeautifulSoup
import time

# Define a simple password
PASSWORD = "aymeric404"

# Check if user is authenticated
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Authentication UI
if not st.session_state.authenticated:
    st.title("🔐 Password Protected Access")
    password_input = st.text_input("Enter Password:", type="password")
    
    if st.button("Login"):
        if password_input == PASSWORD:
            st.session_state.authenticated = True
            st.success("✅ Access Granted! You can now use the scraper.")
            st.rerun()
        else:
            st.error("❌ Incorrect Password!")

# Main scraper UI
if st.session_state.authenticated:
    st.title("Otodom Property Scraper")
    st.write("Scraping property listings from Otodom with Requests & BeautifulSoup...")

    # Fetch the total number of pages dynamically
    url_template = "https://www.otodom.pl/pl/wyniki/sprzedaz/inwestycja/mazowieckie/warszawa/warszawa/warszawa?ownerTypeSingleSelect=ALL&viewType=listing&limit=72&page=1"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    
    # Get the first page to extract the total number of pages
    response = requests.get(url_template, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        pagination = soup.select("ul.pagination li a")
        total_pages = 1  # Default if no pagination found
        if pagination:
            total_pages = max([int(page.get_text()) for page in pagination if page.get_text().isdigit()])
    else:
        st.error(f"❌ Failed to retrieve page (Status: {response.status_code})")
        total_pages = 1
    
    # Let the user select the maximum number of pages
    max_pages = st.number_input("Max pages to scrape", min_value=1, max_value=total_pages, value=1, step=1)

    if st.button("Start Scraping"):
        progress_bar = st.progress(0)
        log_messages = []
        url_template = "https://www.otodom.pl/pl/wyniki/sprzedaz/inwestycja/mazowieckie/warszawa/warszawa/warszawa?ownerTypeSingleSelect=ALL&viewType=listing&limit=72&page={}"
        
        links = []
        scraped_data = []
        log_placeholder = st.empty()
        dataframe = st.empty()
        
        for page in range(1, max_pages + 1):
            url = url_template.format(page)
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                log_messages.append(f"❌ Failed to retrieve page {page} (Status: {response.status_code})")
                break
            
            soup = BeautifulSoup(response.text, "html.parser")
            listing_elements = soup.select("a[data-cy='listing-item-link']")
            
            if not listing_elements:
                log_messages.append(f"❌ No listings found on page {page}. Stopping.")
                break
            
            new_links = list(set(element.get("href") for element in listing_elements))
            links.extend(new_links)
            
            log_messages.append(f"✅ Scraped {len(new_links)} links from page {page}")
            progress_bar.progress(page / max_pages)
            time.sleep(1)
            log_placeholder.text_area("📜 Scraper Log", "\n".join(log_messages), height=300)
        
        links = list(set(links))
        log_messages.append(f"🔗 Total unique property links collected: {len(links)}")
        log_placeholder.text_area("📜 Scraper Log", "\n".join(log_messages), height=300)
        
        for index, link in enumerate(links):
            full_link = f"https://www.otodom.pl{link}" if link.startswith("/") else link
            response = requests.get(full_link, headers=headers)
            
            if response.status_code != 200:
                log_messages.append(f"⚠️ Failed to retrieve listing {full_link}")
                continue
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            element = soup.find("p", text="Dostępne lokale")
            
            first_number, second_number = None, None
            if element and element.find_next_sibling("p"):
                numbers = element.find_next_sibling("p").text.split(" z ")
                first_number, second_number = numbers if len(numbers) == 2 else (None, None)
            
            scraped_data.append([ 
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                full_link,
                first_number,
                second_number
            ])
            
            log_messages.append(f"📌 Scraped {index+1}/{len(links)}: {full_link}")
            df = pd.DataFrame(scraped_data, columns=["Date of Extraction", "URL", "First Number", "Second Number"])
            progress_bar.progress((index + 1) / len(links))
            log_placeholder.text_area("📜 Scraper Log", "\n".join(log_messages), height=300)
            dataframe.table(df)
            time.sleep(1)
        
        st.success(f"✅ Scraping complete! {len(scraped_data)} properties collected.")
        
        excel_file = io.BytesIO()
        df.to_excel(excel_file, index=False, engine='openpyxl')
        excel_file.seek(0)
        
        st.download_button(
            label="📥 Download Excel",
            data=excel_file,
            file_name="otodom_listings.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
