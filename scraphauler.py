import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

def scrape_image(search_term):
	# Replace spaces with underscores in search_term
	search_term = search_term.replace(" ", "_")
	# URL encode the search term to handle special characters
	encoded_term = quote(search_term)
	url = f"http://foxhole.wiki.gg/{encoded_term}?action=pagevalues"
	print(f"{url}")

	# Fetch the webpage
	response = requests.get(url)

	if response.status_code == 200:
		soup = BeautifulSoup(response.content, "html.parser")
		
		# Find the image with class "thumbimage"
		img_tag = soup.find("img", {"class": ["thumbimage", "thumbinner"]})
		
		if img_tag:
			# Get the image source (src) URL
			img_url = img_tag['src']
			# Make it a full URL by adding the base URL	
			img_url = f"http://foxhole.wiki.gg{img_url}"
			return img_url
		else:
			return "No image found"
	else:
		return f"Failed to retrieve page. Status code: {response.status_code}"
		
def scrape_item_data(search_term):
	# Replace spaces with underscores in search_term
	search_term = search_term.replace(" ", "_")
	# URL encode the search term to handle special characters
	encoded_term = quote(search_term)
	url = f"http://foxhole.wiki.gg/{encoded_term}?action=pagevalues"
	print(f"{url}")

	# Fetch the webpage
	response = requests.get(url)

	if response.status_code == 200:
		soup = BeautifulSoup(response.content, "html.parser")
		
		# Find the image
		img_tag = soup.find("img", {"class": "thumbimage"})
		img_url = None
		if img_tag:
			img_url = f"http://foxhole.wiki.gg{img_tag['src']}"
			
		# Scrap production price
		price_tag = soup.find("span", {"class": "price"})
		price = price_tag.text if price_tag else "No price found"
		
		# Find the factory
		factory_tag = soup.find("span", {"class": "factory"})
		factory = factory_tag.text if factory_tag else "No factory found"
		
		# Find the materials
		madeof_tag = soup.find("span", {"class": "madeof"})
		madeof = madeof_tag.text if madeof_tag else "No materials found"
		
		# Return a dictionary of all the scraped data
		return {
			"image_url": img_url,
			"price": price,
			"factory": factory,
			"madeof": madeof
		}
	else:
		return f"Failed to retrieve page. Status code: {response.status_code}"
