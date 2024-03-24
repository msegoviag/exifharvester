<p align="center">
  <img src="https://github.com/msegoviag/exifharvester/assets/41863090/ea654f13-dbea-4029-b1b6-91b6be46d0d7" height=150 width=250><br>
  <hr>

  <b>Automatic tool for extracting EXIF metadata from website images and sets of URLs.
  A perfect tool for bug hunters and OSINT researchers.</b><br>

  Features 🪄
----------
- Get EXIF metadata from website images quickly and in real-time
- Nominatim API integration for fast location detection
- Download all images from a website in a few seconds
- Base64 image support
- INPUT supported: STDIN, URL and LIST
- OUTPUT supported: FILE
- Detecting images with EXIF GPS metadata is a valid vulnerability in BUG BOUNTY PROGRAMS! (P3 -P4): "EXIF Geolocation Data Not Stripped From Uploaded Images"

Installation ⚙️
----------

```bash
git clone https://github.com/msegoviag/exifharvester.git 
```
```bash
cd exifharvester
```
```bash
python exifharvester.py -u dpreview.com -i 1
```

Dependencies 🛠️
----------
The following external libraries may need to be installed: `urllib3`, `requests`, `beautifulsoup4` and `Pillow`

These dependencies can be installed using the requirements.txt file:

- Installation on Linux and MacOS
```
pip install -r requirements.txt
```
- Installation on Windows:
```
python.exe -m pip install -r requirements.txt
```
Usage 🚀
----------
<p align="center">

  <img src="https://github.com/msegoviag/exifharvester/assets/41863090/0f54aef9-5b99-461a-a4cd-5f0edd9b16f0" style="max-width: 100%; height: auto; object-fit: cover; display: inline-block;" data-target="animated-image.originalImage">

Examples of use 💡
----------
### Scan a website
`python exifharvester.py -u dpreview.com`

### Scan a website (STDIN)
`echo dpreview.com | python exifharvester.py`<br>
`cat urls.txt | python exifharvester.py`

### Scan a website (LIST)
`python exifharvester.py -f urls.txt`

### Scan local images
`python exifharvester.py -l 1337.jpg`

### Download the images and save the EXIF results 
`python exifharvester.py -u dpreview.com -s DownloadedImages -o results.txt`

### Display raw EXIF data 
`python exifharvester.py -u dpreview.com --raw`

### Set Cookie for auth
`python exifharvester.py -u test.com -C PHPSESSID=e1faf854faf7fa62f1`

### Set new User-Agent
`python exifharvester.py -u test.com -ua "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"`

### Set proxy
`python exifharvester.py -u test.com -p 127.0.0.1:8118`

### Threads
`python exifharvester.py -u dpreview.com -t 15`

### Scan a website and crawling
`python exifharvester.py -u dpreview.com -cr`<br>
`python exifharvester.py -u dpreview.com -cr -d 4` (depth)

### Ignore errors
`python exifharvester.py -u dpreview.com -i 1` (ignore errors and shows informative results) <br>
`python exifharvester.py -u dpreview.com -i 2` (silent)

### API
`python exifharvester.py -u dpreview.com -api 0` (The Nominatim API is not used) <br>
`python exifharvester.py -u dpreview.com -api 1` (The use of the Nominatim API is enforced)

### Print the help
`python exifharvester.py -h`

## Support this project 🤑

<p dir="auto"><a href="https://www.buymeacoffee.com/msegoviag
" rel="nofollow"><img src="https://camo.githubusercontent.com/151fc5b863df6c6ee657ce46b0308a7cde0e9af5fb7b2b1a244af1f9b4350161/68747470733a2f2f63646e2e6275796d6561636f666665652e636f6d2f627574746f6e732f76322f64656661756c742d677265656e2e706e67" data-canonical-src="https://cdn.buymeacoffee.com/buttons/v2/default-green.png" style="max-width: 100%;"></a></p>

## ToDo ⛏️

Selenium support for detecting images that are dynamically loaded with Javascript, a common behaviour in several frameworks.

## License ⚖️

Exifharvester is licensed under the GNU GPL license. take a look at the [LICENSE](https://github.com/msegoviag/exifharvester/blob/main/LICENSE.txt) for more information.

## Disclaimer of responsibility 🚨

Usage of this program for attacking targets without consent is illegal. It is the user's responsibility to obey all applicable laws. The developer assumes no liability and is not responsible for any misuse or damage caused by this program. Please use responsibly.

