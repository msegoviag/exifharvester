<p align="center">
  <img src="https://github.com/msegoviag/exifharvester/assets/41863090/ea654f13-dbea-4029-b1b6-91b6be46d0d7" height=150 width=250><br>
  <hr>

  <b>Automatic tool for extracting EXIF metadata from website images and sets of URLs.
  A perfect tool for bug hunters and OSINT researchers.</b><br>

  Installation ⚙️
----------

```bash
git clone https://github.com/msegoviag/exifharvester.git
```

Dependencies 🛠️
----------
The following external libraries may need to be installed: `urllib3`, `requests`, `beautifulsoup4` and `Pillow`

These dependencies can be installed using the requirements.txt file:

- Installation on Windows:
```
python.exe -m pip install -r requirements.txt
```
- Installation on Linux and MacOS
```
sudo pip install -r requirements.txt
```
Usage 🚀
----------
<p align="center">

  <img src="https://github.com/msegoviag/exifharvester/assets/41863090/0f54aef9-5b99-461a-a4cd-5f0edd9b16f0" style="max-width: 100%; height: auto; object-fit: cover; display: inline-block;" data-target="animated-image.originalImage">

Examples of use 💡
----------
### Scan a website
`python exifharvester.py -u youtube.com` 
### Print the help
`python exifharvester.py -h` 



