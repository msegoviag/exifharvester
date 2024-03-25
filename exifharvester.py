#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import json
import time
import base64
import urllib3
import warnings
import requests
import argparse
import urllib.parse
from io import BytesIO
import concurrent.futures
from bs4 import BeautifulSoup
from urllib3.exceptions import InsecureRequestWarning
from PIL import Image, ExifTags, UnidentifiedImageError
from urllib.parse import urljoin, urlparse, urlencode, unquote

banner = """
  ______ __   __ _____  ______  _    _            _____ __      __ ______   _____  _______  ______  _____  
 |  ____|\ \ / /|_   _||  ____|| |  | |    /\    |  __ \\ \    / /|  ____| / ____||__   __||  ____||  __ \ 
 | |__    \ V /   | |  | |__   | |__| |   /  \   | |__) |\ \  / / | |__   | (___     | |   | |__   | |__) |
 |  __|    > <    | |  |  __|  |  __  |  / /\ \  |  _  /  \ \/ /  |  __|   \___ \    | |   |  __|  |  _  / 
 | |____  / . \  _| |_ | |     | |  | | / ____ \ | | \ \   \  /   | |____  ____) |   | |   | |____ | | \ \ 
 |______|/_/ \_\|_____||_|     |_|  |_|/_/    \_\|_|  \_\   \/    |______||_____/    |_|   |______||_|  \_\     v1.0                                                                                                                                                                                                
"""

# Session object to keep cookies between requests
session = requests.Session()

HTTP_PREFIX = 'http://'
HTTPS_PREFIX = 'https://'
Image.MAX_IMAGE_PIXELS = None
urllib3.disable_warnings(InsecureRequestWarning)
warnings.simplefilter('ignore', InsecureRequestWarning)

exif_counters = {'with_exif': 0, 'without_exif': 0, 'with_relevant_exif': 0, 'excluded': 0}
processed_images = set()

def ensure_url_scheme(url):
    if not url.startswith((HTTP_PREFIX, HTTPS_PREFIX)):
        return HTTP_PREFIX + url
    return url

def ensure_absolute_url(url, base_url):
    
    # If the URL already has a scheme, it's already absolute.
    if url.startswith((HTTP_PREFIX, HTTPS_PREFIX)):
        return url

    # If the URL starts with //, it's a protocol-relative URL.
    if url.startswith('//'):
        scheme = urlparse(base_url).scheme
        return f'{scheme}:{url}'

    return urljoin(base_url, url)
    
def read_urls_from_stdin():
    urls = []
    for line in sys.stdin:
        urls.append(line.strip())
    return urls

def show_banner():
    print(banner)
    print("\t\t\t\t\t\t\t\t\t\t\tMiguel Segovia (msegoviag)\n")
    
def is_base64_image(image_url):
    return image_url.startswith('data:image/')

def is_image_url(url, user_agent=None):
    try:
        headers = {'User-Agent': user_agent} if user_agent else {}
        response = session.head(url, allow_redirects=True, headers=headers)
        content_type = response.headers.get('Content-Type', '')
        return 'image' in content_type
    except requests.RequestException:
        return False

def format_raw_metadata(metadata):
    return "\n".join(f"{ExifTags.TAGS.get(key, key)}: {value}" for key, value in metadata.items())

def truncate_base64_url(url, max_length=50):
    if url.startswith("data:image") and len(url) > max_length:
        return url[:max_length] + '...'
    return url

def print_metadata(image_url, metadata, file=None):
    output = f"\n✅ EXIF Data Of {image_url}:\n{metadata}\n"
    print(output, end='')
    if file:
        with open(file, "a", encoding='utf-8') as f:
            f.write(output)

def decode_base64_image(base64_str):
    """Decode a Base64 encoded image."""
    base64_data = base64_str.split(';base64,')[1]
    return base64.b64decode(base64_data) 

def decode_unicode_escape(url):
    """Decodes escape sequences in URL."""
    return unquote(url)

def extract_image_from_img_tag(img_tag, base_url):
    if 'src' in img_tag.attrs:
        decoded_url = decode_unicode_escape(img_tag['src'])
        return ensure_absolute_url(decoded_url, base_url)
    else:
        return None

def extract_image_from_a_tag(a_tag, base_url):
    href = a_tag.get('href', '')
    if href.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico', '.webp')):
        decoded_href = decode_unicode_escape(href)
        return ensure_absolute_url(decoded_href, base_url)
    return None

def extract_image_from_div_tag(div_tag, base_url):
    style = div_tag.get('style', '')
    match = re.search(r'url\((.*?)\)', style)
    if match:
        image_url = match.group(1).strip("'\"")
        decoded_url = decode_unicode_escape(image_url)
        return ensure_absolute_url(decoded_url, base_url)
    else:
        return None

def extract_image_from_data_src_div(div_tag, base_url):
    if 'data-src' in div_tag.attrs:
        decoded_url = decode_unicode_escape(div_tag['data-src'])
        return ensure_absolute_url(decoded_url, base_url)
    else:
        return None

def extract_image_from_meta_tag(meta_tag, base_url):
    if 'content' in meta_tag.attrs:
        decoded_content = decode_unicode_escape(meta_tag['content'])
        return ensure_absolute_url(decoded_content, base_url)
    else:
        return None

def extract_image_from_link_tag(link_tag, base_url):
    if 'href' in link_tag.attrs:
        decoded_href = decode_unicode_escape(link_tag['href'])
        return ensure_absolute_url(decoded_href, base_url)
    else:
        return None

def extract_image_from_source_tag(source_tag, base_url):
    if 'srcset' in source_tag.attrs:
        srcset = source_tag['srcset']
        first_source_url = srcset.split(',')[0].split(' ')[0]
        decoded_url = decode_unicode_escape(first_source_url)
        return ensure_absolute_url(decoded_url, base_url) if first_source_url else None
    else:
        return None

def extract_images_general(html, base_url):
    image_urls = set()

    patterns = [
        r'<img[^>]+src="([^"]+)"',
        r'<link[^>]+href="([^"]+\.(jpg|jpeg|png|gif|bmp|svg|ico|webp))"[^>]*>',
        r'<meta[^>]+content="([^"]+\.(jpg|jpeg|png|gif|bmp|svg|ico|webp))"[^>]*>', 
        r'src=\\"([^"]+)\\"',
        r'background-image:\s*url\((?:\'([^\']+)\'|\"([^\"]+)\"|([^\'\"\)]+))\)',
        r'url\(([^)]+\.(jpg|jpeg|png|gif|bmp|svg|ico|webp))\)',
        r'data-src="([^"]+\.(jpg|jpeg|png|gif|bmp|svg|ico|webp))"',
        r'["\'](?:rawBlobUrl|displayUrl)["\']:\s*["\']([^"\']+?\.(jpg|jpeg|png|gif|bmp|svg|webp))["\']', # Dealing with GitHub issues...
    ]

    for pattern in patterns:
        for match in re.findall(pattern, html, re.IGNORECASE):
            url = match if isinstance(match, str) else match[0]
            decoded_url = decode_unicode_escape(url)
            image_url = urljoin(base_url, decoded_url)
            image_urls.add(image_url)
            
    return image_urls

def get_image_urls(base_url, proxy=None, ignore_errors=0, user_agent=None, exclude_paths=None):
    base_url = ensure_url_scheme(base_url)
    if proxy:
        session.proxies.update({'http': f'http://{proxy}', 'https': f'http://{proxy}'})
    if user_agent:
        session.headers.update({'User-Agent': user_agent})

    try:
        response = session.get(base_url)
        response.raise_for_status()
        html = response.text

        image_urls_specific = set()
        soup = BeautifulSoup(html, 'html.parser')

        # Specific tag extractors
        tag_extractors = {
            'img': extract_image_from_img_tag,
            'div': extract_image_from_div_tag,
            'div[data-src]': extract_image_from_data_src_div,
            'meta[property="og:image"]': extract_image_from_meta_tag,
            'link[rel="icon"][type="image/x-icon"]': extract_image_from_link_tag,
            'picture source[type="image/webp"][srcset]': extract_image_from_source_tag,
            'a': extract_image_from_a_tag,
        }

        for tag, extractor in tag_extractors.items():
            for tag_instance in soup.select(tag):
                image_url = extractor(tag_instance, base_url)
                if image_url:
                    image_urls_specific.add(image_url)

        image_urls_general = extract_images_general(html, base_url)

        all_image_urls = image_urls_specific.union(image_urls_general)
        filtered_image_urls = set()

        if exclude_paths is None:
            exclude_paths = [] 
      
        exclude_regex = re.compile('|'.join(map(re.escape, exclude_paths)), re.IGNORECASE) if exclude_paths else None

        for url in all_image_urls:
            if (not url.lower().endswith(('.svg', '.svg+xml'))) and (not exclude_regex.search(url) if exclude_regex else True):
                filtered_image_urls.add(url)
            else:
                exif_counters['excluded'] += 1
                processed_images.add(url)
                if not ignore_errors:
                    print(f"⚠️  Image excluded: {url}")

        return list(filtered_image_urls)

    except requests.RequestException as e:
        if not ignore_errors:
            print(f"❌ Error fetching image URLs from {base_url}: {e}")
        return []

def get_relevant_metadata(exif_data):
    exif_tags = {v: k for k, v in ExifTags.TAGS.items()}
    relevant_tags = {
        "Make": "\t📱 Brand",
        "Model": "\t📱 Model",
        "DateTime": "\t🕥 Date and time",
        "GPSInfo": "\t🌍 GPS Location",
        "Software": "\t📀 Software"
    }
    relevant_metadata = {}
    for tag, desc in relevant_tags.items():
        tag_key = exif_tags.get(tag)
        if tag_key and tag_key in exif_data:
            if tag == "GPSInfo":
                gps_info = exif_data[tag_key]
                gps_data = {ExifTags.GPSTAGS.get(key): value for key, value in gps_info.items()}
                relevant_metadata[desc] = gps_data
            else:
                relevant_metadata[desc] = exif_data[tag_key]
    return relevant_metadata

# Nominatim's free API is a bit bullshit, I encourage you to use another one if you want to

def get_location_info(lat, lon, use_api=1):
    if use_api == 0:
        return "API disabled. Location information not available."

    try:
        base_url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json"
        }
        url = f"{base_url}?{urlencode(params)}"
        response = session.get(url)

        if response.status_code == 200:
            data = response.json()
            city = data.get('address', {}).get('city', 'Unknown')
            country = data.get('address', {}).get('country', 'Unknown')
            state = data.get('address', {}).get('state', 'Unknown')
            quarter = data.get('address', {}).get('quarter', 'Unknown')
            neighbourhood = data.get('address', {}).get('neighbourhood', 'Unknown')
            road = data.get('address', {}).get('road', 'Unknown')
            village = data.get('address', {}).get('village', 'Unknown')
            return f"Country: {country}, City: {city}, State: {state}, Quarter: {quarter}, Neighbourhood: {neighbourhood}, Village: {village}, Road: {road} "
        else:
            return "Error retrieving location information"
    except Exception as e:
        print(f"Error retrieving location information: {e}")
        return None
    
def get_image_metadata(image_data, proxy=None, ignore_errors=0, user_agent=None):
    try:
        if is_base64_image(image_data):
            image_bytes = decode_base64_image(image_data)
            image = Image.open(BytesIO(image_bytes))
        else:
            image_url = ensure_url_scheme(image_data)
            proxies = {'http': f'http://{proxy}', 'https': f'http://{proxy}'} if proxy else None
            headers = {'User-Agent': user_agent} if user_agent and isinstance(user_agent, str) else None
            response = session.get(image_url, proxies=proxies, headers=headers, verify=False)
            
            if 'image' not in response.headers.get('Content-Type', ''):
                if not ignore_errors:
                    print(f"\n❌ The URL {image_url} does not point to an image or is no longer available.")
                return None
            image = Image.open(BytesIO(response.content))

        exif_data = image._getexif()
        return exif_data
    
    except requests.exceptions.RequestException as e:
        if not ignore_errors:
            if is_base64_image(image_data):
                truncated_image_url = truncate_base64_url(image_data)
            else:
                truncated_image_url = image_data
            print(f"❌ Error obtaining information from: {truncated_image_url}\n")
        return None
    except UnidentifiedImageError:
        if not ignore_errors:
            if is_base64_image(image_data):
                truncated_image_url = truncate_base64_url(image_data)   
            else:
                truncated_image_url = image_data
            print(f"❌ Could not identify the image in the URL {truncated_image_url}. The format may not be supported.")
        return None
    except Exception as e:
        if not ignore_errors:
            if is_base64_image(image_data):
                truncated_image_url = truncate_base64_url(image_data)
            else:
                truncated_image_url = image_data
            print(f"❌ Error obtaining information from: {truncated_image_url}\n")
        return None

def get_internal_links(url, visited, proxy=None, depth=0, max_depth=4, cookie=None, user_agent=None, exclude_paths=None):
    if depth > max_depth:
        return set()

    url = ensure_url_scheme(url)
    base_domain = urlparse(url).netloc
    headers = {'Cookie': cookie} if cookie else {}
    headers.update({'User-Agent': user_agent}) if user_agent else None
    proxies = {'http': f'http://{proxy}', 'https': f'http://{proxy}'} if proxy else None
    response = session.get(url, proxies=proxies, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    links = set()

    ## Common logout endpoints regex pattern cause crawler logout. Add more whether needed or use -e option
    default_exclude_patterns = ['/logout', '/signout', '/sign_out']

    if exclude_paths:
        combined_exclude_patterns = default_exclude_patterns + exclude_paths
    else:
        combined_exclude_patterns = default_exclude_patterns

    exclude_regex = re.compile('|'.join(map(re.escape, combined_exclude_patterns)), re.IGNORECASE)

    for link in soup.find_all('a', href=True):
        href = link['href']
        full_url = ensure_absolute_url(href, url)
        if urlparse(full_url).netloc == base_domain and full_url not in visited:
            if not exclude_regex.search(full_url):
                links.add(full_url)

    return links

def get_image_metadata_from_file(file_path):
    try:
        with Image.open(file_path) as image:
            exif_data = image._getexif()
            return exif_data
    except UnidentifiedImageError:
        print(f"❌ Could not identify the image in {file_path}. The format may not be supported.")
        return None
    except Exception as e:
        print(f"❌ Error processing the image of {file_path}: {e}")
        return None

def format_gps_data(gps_data):
    try:
        lat_ref = gps_data.get('GPSLatitudeRef', '')
        lat = gps_data.get('GPSLatitude')
        lon_ref = gps_data.get('GPSLongitudeRef', '')
        lon = gps_data.get('GPSLongitude')

        formatted_lat = float(lat[0]) + float(lat[1]) / 60 + float(lat[2]) / 3600
        formatted_lon = float(lon[0]) + float(lon[1]) / 60 + float(lon[2]) / 3600

        formatted_lat_str = f"{formatted_lat:.6f}° {lat_ref}"
        formatted_lon_str = f"{formatted_lon:.6f}° {lon_ref}"

        return formatted_lat, formatted_lon, formatted_lat_str, formatted_lon_str
    except TypeError:
        return None, None, "Not Available", "Not Available"

def print_beautiful_metadata(image_url, metadata, file=None, ignore_errors=0):
    if is_base64_image(image_url):
        # Truncate the Base64 string for display :)
        image_url_display = image_url[:30] + "..." + image_url[-30:]
    else:
        image_url_display = image_url

    output = f"\n✅ EXIF Data Of {image_url_display}:\n"
    relevant_metadata_found = False

    # Process and add GPS location information
    gps_info = metadata.get('\t🌍 GPS Location', {})
    if gps_info:
        lat, lon, lat_str, lon_str = format_gps_data(gps_info)
        if lat is not None and lon is not None:
            # Get location information using Nominatim API
            location_info = get_location_info(lat, lon, use_api=args.use_api)
            output += f"\t🌍 GPS Location: {lat_str}, {lon_str}"
            if location_info and location_info != "Error retrieving location information":
                output += f" ({location_info})"
            output += "\n"
            relevant_metadata_found = True
        elif not ignore_errors:
            output += "\t🌍 GPS Location: Not Available\n"

    for key, value in metadata.items():
        if key != '\t🌍 GPS Location':
            output += f"  {key}: {value}\n"
            relevant_metadata_found = True

    # Add a line break if relevant metadata was found
    if relevant_metadata_found:
        output += "\n" 
        print(output, end='')
        if file:
            with open(file, "a", encoding='utf-8') as f:
                f.write(output)
    else:
        if not ignore_errors:
            if is_base64_image(image_url):
                truncated_image_url = truncate_base64_url(image_url)
            else:
                truncated_image_url = image_url
    
            print(f"❌ No EXIF metadata found for the image: {truncated_image_url}\n")
            
def save_base64_image(base64_str, save_folder):
    try:
        image_data = decode_base64_image(base64_str)
        image = Image.open(BytesIO(image_data))
        # Create a unique file name based on the current time and save the image
        file_name = "image_{}.png".format(int(time.time()))
        file_path = os.path.join(save_folder, file_name)
        
        image.save(file_path)
        return f"\t💾 Saved image: {file_path}\n"
    except Exception as e:
        return f"❌ Error saving Base64 image: {e}\n"

def download_and_save_image(image_url, save_folder):
    try:
        response = session.get(image_url)
        if response.status_code == 200:

            image_content = response.content

            parsed_url = urllib.parse.urlparse(image_url)
            file_name = os.path.basename(parsed_url.path)

            content_type = response.headers.get('Content-Type', '')
            extension_map = {
                'image/jpeg': '.jpg',
                'image/png': '.png',
                'image/gif': '.gif',
                'image/tiff': '.tif',
                'image/bmp': '.bmp',
                'image/x-icon': '.ico',
                'image/svg+xml': '.svg',
                'image/webp': '.webp',
            }
            
            extension = extension_map.get(content_type, '')

            if not extension:
                extension = '.jpg'

            file_name = re.sub(r'[<>:"/\\|?*]', '', file_name)
            file_name = os.path.splitext(file_name)[0] + extension
            file_path = os.path.join(save_folder, file_name)

            with open(file_path, 'wb') as image_file:
                image_file.write(image_content)
            return f"\t💾 Saved image: {file_path}\n"
        else:
            return f"❌ Could not download image from: {image_url}\n"
    except Exception as e:
        return f"❌ Error downloading image from: {image_url}: {e}\n"           
                       
def print_final_statistics(processed_images, exif_counters):
    total_images = len(processed_images)
    with_relevant_exif = exif_counters['with_relevant_exif']
    with_exif = exif_counters['with_exif'] - with_relevant_exif
    without_exif = exif_counters['without_exif']
    excluded = exif_counters['excluded']
    
    max_number_length = max(len(str(total_images)), len(str(with_relevant_exif)), len(str(with_exif)), len(str(without_exif)), len(str(excluded)))

    number_column_width = max_number_length + 2

    labels = [
        "Total processed images:",
        "Images with relevant EXIF:",
        "Images without relevant EXIF",
        "Images without any EXIF:",
        "Excluded images:"
    ]
    max_label_length = max(len(label) for label in labels)
    table_width = max_label_length + number_column_width + 5

    print("┌" + "─" * (table_width - 2) + "┐")
    print(f"│ {'🏁 Image Analysis Completed'.center(table_width - 4)}│")
    print("├" + "─" * (table_width - 2) + "┤")
    print(f"│ {'Total processed images:':<{max_label_length}} {total_images:>{number_column_width}} │")
    print(f"│ {'Images with relevant EXIF:':<{max_label_length}} {with_relevant_exif:>{number_column_width}} │")
    print(f"│ {'Images without relevant EXIF':<{max_label_length}} {with_exif:>{number_column_width}} │")
    print(f"│ {'Images without any EXIF:':<{max_label_length}} {without_exif:>{number_column_width}} │")
    print(f"│ {'Excluded Images:':<{max_label_length}} {excluded:>{number_column_width}} │")
    print("└" + "─" * (table_width - 2) + "┘")

def process_single_image(image_url, processed_images, proxy=None, raw=False, output_file=None, save=False, save_folder=None, ignore_errors=0, user_agent=None):
    global exif_counters

    if image_url in processed_images:
        return

    if not is_base64_image(image_url):
        image_url = ensure_url_scheme(image_url)

    metadata = get_image_metadata(image_url, proxy, ignore_errors, user_agent)
    if metadata:
        exif_counters['with_exif'] += 1
        relevant_metadata = get_relevant_metadata(metadata)
        if relevant_metadata:
            exif_counters['with_relevant_exif'] += 1
            
            if raw:
                formatted_metadata = format_raw_metadata(metadata)
                print_metadata(image_url, formatted_metadata, output_file)
            else:
                print_beautiful_metadata(image_url, relevant_metadata, output_file, ignore_errors)
        else:
            if raw:
                formatted_metadata = format_raw_metadata(metadata)
                print_metadata(image_url, formatted_metadata, output_file)
            elif ignore_errors != 2:
                print(f"ℹ️ Image {image_url} has EXIF but no relevant metadata found.\n")
    else:
        exif_counters['without_exif'] += 1
        if not ignore_errors:
            if is_base64_image(image_url):
                truncated_image_url = truncate_base64_url(image_url)
            else:
                truncated_image_url = image_url
    
            print(f"❌ No EXIF metadata found for the image: {truncated_image_url}\n")

    processed_images.add(image_url)

    if save and save_folder:
        if is_base64_image(image_url):
            saved_msg = save_base64_image(image_url, save_folder)
        else:
            saved_msg = download_and_save_image(image_url, save_folder)
        if "Saved" in saved_msg:
            print(saved_msg)

    return exif_counters

def crawler_main(base_url, proxy=None, raw=False, output_file=None, cookie=None, user_agent=None, save=False, save_folder="output", max_depth=4, ignore_errors=0):
    visited_urls = set()
    urls_to_visit = {base_url}

    while urls_to_visit:
        current_url = urls_to_visit.pop()
        if current_url in visited_urls:
            continue

        visited_urls.add(current_url)
        print(f"\n🕷️ 🕸️  Browsing: {current_url}\n")

        try:
            internal_links = get_internal_links(current_url, visited_urls, proxy, depth=len(visited_urls), cookie=cookie, user_agent=user_agent, max_depth=max_depth, exclude_paths=exclude_paths)
            urls_to_visit.update(link for link in internal_links if link not in visited_urls)

            image_urls = get_image_urls(current_url, proxy, ignore_errors, exclude_paths=args.exclude)
            for image_url in image_urls:
                if image_url not in processed_images:
                    process_single_image(image_url, processed_images, proxy, raw, output_file, save, save_folder, ignore_errors)
                    if save:
                        download_and_save_image(image_url, save_folder)
        except Exception as e:
            if not ignore_errors:
                print(f"❌ Error processing {current_url}: {e}")

    print("\n🏁 The crawler has finished running.\n")

def process_local_image(path, raw=False, output_file=None):
    
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.ico', '.svg'}

    if os.path.isdir(path):
     
        for filename in os.listdir(path):
            file_path = os.path.join(path, filename)
            _, extension = os.path.splitext(filename)

            if extension.lower() in allowed_extensions:
                process_image_path(file_path, raw, output_file)
                
    elif os.path.isfile(path):
        process_image_path(path, raw, output_file)
    else:
        print(f"❌ {path} Invalid Path. Please provide a valid file or directory.")

def process_image_path(file_path, raw, output_file):
    
    metadata = get_image_metadata_from_file(file_path)
    if metadata:
        if raw:
            formatted_metadata = format_raw_metadata(metadata)
            print_metadata(file_path, formatted_metadata, output_file)
        else:
            metadata = get_relevant_metadata(metadata)
            print_beautiful_metadata(file_path, metadata, output_file, ignore_errors=0)
    else:
        print(f"\n❌ No metadata found for the image {file_path}")

def process_single_image_wrapper(args):
    process_single_image(*args)
    
def download_and_save_image_wrapper(args):
    download_and_save_image(*args)

def process_images_concurrently(url, raw, output_file, processed_images, proxy, save, save_folder, max_threads=5, ignore_errors=0):
    
    image_urls = get_image_urls(url, proxy, ignore_errors, user_agent=None, exclude_paths=args.exclude)

    if not image_urls:
        return False

    with concurrent.futures.ThreadPoolExecutor(max_threads) as executor:
        args_list = [(image_url, processed_images, proxy, raw, output_file, save, save_folder, ignore_errors) for image_url in image_urls]
        executor.map(process_single_image_wrapper, args_list)

    return True

def process_images_concurrently_from_file(urls, raw, output_file, processed_images, proxy, save, save_folder, max_threads=5, ignore_errors=0):
    with concurrent.futures.ThreadPoolExecutor(max_threads) as executor:
        
        args_list = []

        for url in urls:
            args_list.append((url, processed_images, proxy, raw, output_file, save, save_folder, ignore_errors))

        executor.map(process_single_image_wrapper, args_list)

    return True

def main_from_stdin(raw, output_file=None, proxy=None, user_agent=None, crawler=False, cookie=None, save=None, depth=4, max_threads=None, ignore_errors=0):
    global processed_images, exif_counters
    
    save_folder = save or "output"
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)
        
    urls = read_urls_from_stdin() if not sys.stdin.isatty() else []

    if urls:
        for url in urls:
            url = ensure_url_scheme(url)
            if proxy:
                session.proxies.update({HTTP_PREFIX: f'http://{proxy}', HTTPS_PREFIX: f'https://{proxy}'})
            if cookie:
                session.headers.update({'Cookie': cookie})
            if user_agent:  
                session.headers.update({'User-Agent': user_agent})

            if is_image_url(url):
                process_single_image(url, processed_images, proxy, raw, output_file, save, save_folder, ignore_errors)
            elif crawler:
                crawler_main(url, proxy, raw, output_file, cookie, user_agent, save, save_folder, depth, ignore_errors)
            else:
                images_found = process_images_concurrently(url, raw, output_file, processed_images, proxy, save, save_folder, max_threads, ignore_errors)
                if not images_found and not ignore_errors:
                    print("❌ No images were found in the URL provided.")
    else:
        print("❌ No valid image URLs were found in the stdin input.")
    
    print_final_statistics(processed_images, exif_counters)

def main(url, raw, output_file=None, proxy=None, user_agent=None, crawler=False, local_file=None, cookie=None, save=False, depth=4, file_path=None, max_threads=5, ignore_errors=0):
    global processed_images, exif_counters
    
    if not (url or local_file or file_path or not sys.stdin.isatty()):
        print("🥲 No action specified. Please provide a URL, local file, or file path. Use -help for more options")
        return
    
    save_folder = "output" if save is None else save
    if save and not os.path.exists(save_folder):
        os.makedirs(save_folder)

    if file_path:
        with open(file_path, 'r') as file:
            urls = [line.strip() for line in file if line.strip()]

            urls_found = False
            
            if max_threads > 1:
                process_images_concurrently_from_file(urls, raw, output_file, processed_images, proxy, save, save_folder, max_threads, ignore_errors)
                urls_found = True
            else:
                for url in urls:
                    urls_found = True
                    process_single_image(url, processed_images, proxy, raw, output_file, save, save_folder, ignore_errors)

            if not urls_found and not ignore_errors:
                print("❌ No valid image URLs were found in the file.")

    if local_file:
        process_local_image(local_file, raw, output_file)
        return

    if url:
        url = ensure_url_scheme(url)
        if proxy:
            session.proxies.update({HTTP_PREFIX: f'http://{proxy}', HTTPS_PREFIX: f'https://{proxy}'})
        if cookie:
            session.headers.update({'Cookie': cookie})
        if user_agent:  
            session.headers.update({'User-Agent': user_agent})

        if is_image_url(url, user_agent=user_agent):
            process_single_image(url, processed_images, proxy, raw, output_file, save, save_folder, ignore_errors)
        elif crawler:
            crawler_main(url, proxy, raw, output_file, cookie, user_agent, save, save_folder, depth, ignore_errors)
        else:
            images_found = process_images_concurrently(url, raw, output_file, processed_images, proxy, save, save_folder, max_threads, ignore_errors)
            if not images_found and not ignore_errors:
                print("❌ No images were found in the URL provided.")
    
    print_final_statistics(processed_images, exif_counters)

if __name__ == "__main__":
    show_banner()
    
    parser = argparse.ArgumentParser(description="Extract the EXIF metadata of images from a web page or local file.")
    parser.add_argument("-u", "--url", nargs='?', help="URL of the webpage to analyze.", default=None)
    parser.add_argument("-i", "--ignore", type=int, choices=[0, 1, 2], default=0, help="1 for ignore errors and exceptions. 2 for show only relevant metadata.")
    parser.add_argument("-l", "--local", help="Path to a local image file.", default=None)
    parser.add_argument("-r", "--raw", action="store_true", help="Displays raw metadata.")
    parser.add_argument("-api", "--use_api", type=int, choices=[0, 1], default=1, help="Use Nominatim API (0 for no, 1 for yes).")
    parser.add_argument("-o", "--output", help="Saves the results to a specified file.")
    parser.add_argument("-p", "--proxy", help="Uses a proxy for HTTP requests. Format: host:port")
    parser.add_argument("-e", "--exclude", action="append",type=str, help="Excludes specified paths from the crawler. Can be used multiple times or separated by commas. Example: -e /logout -e /profile, /sign_out")
    parser.add_argument("-cr", "--crawler", action="store_true", help="Activates crawler mode.")
    parser.add_argument("-c", "--cookie", help="Cookie for website authentication. Example: -c PHPSESSID=e1faf854faf7fa62f1", default=None)
    parser.add_argument("-s", "--save", nargs='?', const="output", default=None, help="Specify the folder to save all found images (defaults to 'output' if no name is given).")
    parser.add_argument("-d", "--depth", type=int, default=3, help="Defines the depth of the crawler scan.")
    parser.add_argument("-f", "--file", help="Path to a text file containing image URLs.", default=None)
    parser.add_argument("-t", "--threads", type=int, default=1, help="Number of threads for concurrent processing.")
    parser.add_argument("-ua", "--user_agent", help="Specify a custom User-Agent for HTTP requests.", default=None)
    
    args = parser.parse_args()
    
    try:
        exclude_paths = []
        if args.exclude:
            for item in args.exclude:
                exclude_paths.extend([path.strip() for path in item.split(',')])
                
        if sys.stdin.isatty():
            main(args.url, args.raw, args.output, args.proxy, args.user_agent, args.crawler, args.local, args.cookie, args.save, args.depth, args.file, args.threads, args.ignore)
        else:
            main_from_stdin(args.raw, args.output, args.proxy, args.user_agent, args.crawler, args.cookie, args.save, args.depth, args.threads, args.ignore)
    except KeyboardInterrupt:
        print("\n🛑 Exiting gracefully...")
        print_final_statistics(processed_images, exif_counters)