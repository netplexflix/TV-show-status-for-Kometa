# 📺 TV Show Status for Kometa

This script checks your [Sonarr](https://sonarr.tv/) for your TV Shows statuses and creates .yml files which can be used by [Kometa](https://kometa.wiki/) to create collections and overlays.</br>

Categories:
*  Shows for which a finale was added which aired in the past x days
*  Shows with upcoming regular episodes within x days
*  Shows for which a new season is airing within x days
*  Shows with upcoming season finales within x days
*  Returning Shows (new episodes or seasons are coming, but not within the timeframes chosen above)
*  Ended Shows (no new episodes or seasons are expected)

Example overlays:
![Image](https://github.com/user-attachments/assets/91b08c66-58ed-417d-a87d-faf24be20896)
---

## ✨ Features
- 🗓️ **Detects upcoming episodes, finales and seasons**: Searches Sonarr for TV show schedules.
- 🏁 **Aired Finale labelling**: Use a separate overlay for shows for which a Finale was added.
-  ▼ **Filters out unmonitored**: Skips show if season/episode is unmonitored. (optional)
-  🪄 **Customizable**: Change date format, collection name, overlay positioning, text, ..
- ℹ️ **Informs**: Lists matched and skipped(unmonitored) TV shows.
- 📝 **Creates .yml**: Creates collection and overlay files which can be used with Kometa.

---

## 🛠️ Installation

### 1️⃣ Download the script
Clone the repository:
```sh
git clone https://github.com/netplexflix/TV-show-status-for-Kometa.git
cd TV-show-status-for-Kometa
```

![#c5f015](https://placehold.co/15x15/c5f015/c5f015.png) Or simply download by pressing the green 'Code' button above and then 'Download Zip'.

### 2️⃣ Extract or move the files to a 'TSSK' subfolder in your Kometa config folder
- Go to your Kometa install folder, then config.
- Create a subfolder named TSSK.
- Put the files in this subfolder. (`config.example.yml`, `TSSK.py` and `requirements.txt`)

### 3️⃣ Install Dependencies
- Ensure you have [Python](https://www.python.org/downloads/) installed (`>=3.9`). <br/>
- Open a Terminal in the script's directory
>[!TIP]
>Windows Users: <br/>
>Go to the TSSK folder (where TSSK.py is). Right mouse click on an empty space in the folder and click `Open in Windows Terminal`
- Install the required dependencies by pasting the following code:
```sh
pip install -r requirements.txt
```

### 4️⃣ Edit your Kometa config
- Open your Kometa config.yml (config/config.yml, NOT config/TSSK/config.yml)
- Under your TV Show library settings, add the paths to the collection and/or overlay .yml files you would like to use.</br>
  (These files will be created in your TSSK folder when you run the script).<br/>

These Overlay files are created:
```
TSSK_TV_ENDED_OVERLAYS.yml
TSSK_TV_FINAL_EPISODE_OVERLAYS.yml
TSSK_TV_NEW_SEASON_OVERLAYS.yml
TSSK_TV_RETURNING_OVERLAYS.yml
TSSK_TV_SEASON_FINALE_OVERLAYS.yml
TSSK_TV_UPCOMING_EPISODE_OVERLAYS.yml
TSSK_TV_UPCOMING_FINALE_OVERLAYS.yml
```

These Collection files are created:
```
TSSK_TV_ENDED_COLLECTION.yml
TSSK_TV_FINAL_EPISODE_COLLECTION.yml
TSSK_TV_NEW_SEASON_COLLECTION.yml
TSSK_TV_RETURNING_COLLECTION.yml
TSSK_TV_SEASON_FINALE_COLLECTION.yml
TSSK_TV_UPCOMING_EPISODE_COLLECTION.yml
TSSK_TV_UPCOMING_FINALE_COLLECTION.yml
```

  Example:
  ```
  TV Shows:
    collection_files:
    - file: P:/Kometa/config/TSSK/TSSK_TV_COLLECTION.yml
    overlay_files:
    - file: P:/KOMETA/config/TSSK/TSSK_TV_NEW_SEASON_OVERLAYS.yml
    - file: P:/KOMETA/config/TSSK/TSSK_TV_UPCOMING_EPISODE_OVERLAYS.yml
    - file: P:/KOMETA/config/TSSK/TSSK_TV_UPCOMING_FINALE_OVERLAYS.yml
    - file: P:/KOMETA/config/TSSK/TSSK_TV_ENDED_OVERLAYS.yml
    - file: P:/KOMETA/config/TSSK/TSSK_TV_RETURNING_OVERLAYS.yml
    - file: P:/KOMETA/config/TSSK/TSSK_TV_SEASON_FINALE_OVERLAYS.yml
    - file: P:/KOMETA/config/TSSK/TSSK_TV_FINAL_EPISODE_OVERLAYS.yml
  ```
>[!NOTE]
>Only add the files to the Kometa config for which you want to create collections or overlays<br/>

### 5️⃣ Edit your configuration file
---

## ⚙️ Configuration
Rename `config.example.yml` to `config.yml` and edit the needed settings:

- **sonarr_url:** Change if needed.
- **sonarr_api_key:** Can be found in Sonarr under settings => General => Security.
- **skip_unmonitored:** Default `true` will skip a show if the upcoming season/episode is unmonitored.
</br>
</br>

For each category, you can change the relevant settings:
- **future_days:** How many days into the future the script should look.
- **recent_days:** How many days in the past the script should look (for aired Finales)
- **collection_name:** The name of the collection.
- **sort_title:** Collection sort title.
- **backdrop:** Change backdrop (the colored banner behind the text) size, color and positioning. [More info here](https://kometa.wiki/en/latest/files/overlays/?h=overlay#backdrop-overlay)
- **text:** Change text color and positioning. [More info here](https://kometa.wiki/en/latest/files/overlays/?h=overlay#text-overlay)
  - **date_format:** The date format to be used on the overlays. e.g.: "yyyy-mm-dd", "mm/dd", "dd/mm", etc.
  - **capitalize_dates:** `true` will capitalize letters in dates.
  - **use_text:** Text to be used on the overlays before the date. e.h.: "NEW SEASON"


>[!NOTE]
> These are date formats you can use:<br/>
> `d`: 1 digit day (1)<br/>
> `dd`: 2 digit day (01)<br/>
> `ddd`: Abbreviated weekday (Mon)<br/>
> `dddd`: Full weekday (Monday)<br/>
><br/>
> `m`: 1 digit month (1)<br/>
> `mm`: 2 digit month (01)<br/>
> `mmm`: Abbreviated month (Jan)<br/>
> `mmmm`: Full month (January)<br/>
><br/>
> `yy`: Two digit year (25)<br/>
> `yyyy`: Full year (2025)
>
>Dividers can be `/`, `-` or a space

---
## 🚀 Usage - Running the Script

Open a Terminal in your script directory and launch the script with:
```sh
python TSSK.py
```
The script will list matched and/or skipped shows and create the .yml files. <br/>
The previous configuration will be erased so Kometa will automatically remove overlays for shows that no longer match the criteria.

> [!TIP]
> Windows users can create a batch file to quickly launch the script.<br/>
> Type `"[path to your python.exe]" "[path to the script]" -r pause"` into a text editor
>
> For example:
> ```
>"C:\Users\User1\AppData\Local\Programs\Python\Python311\python.exe" "P:\Kometa\config\TSSK\TSSK.py" -r
>pause
> ```
> Save as a .bat file. You can now double click this batch file to directly launch the script.<br/>
> You can also use this batch file to [schedule](https://www.windowscentral.com/how-create-automated-task-using-task-scheduler-windows-10) the script to run.
---


### ⚠️ **Do you Need Help or have Feedback?**
- Join the [Discord](https://discord.gg/VBNUJd7tx3).

---
## ？ FAQ
**Is there a docker container?**<br/>
I made this for my personal use. I don't use docker myself and have no plans atm to learn how to make dockerfiles.<br/>
If anyone wants to help make one, please feel free to create a pull request!
  
---  
### ❤️ Support the Project
If you like this project, please ⭐ star the repository and share it with the community!

<br/>

[!["Buy Me A Coffee"](https://github.com/user-attachments/assets/5c30b977-2d31-4266-830e-b8c993996ce7)](https://www.buymeacoffee.com/neekokeen)
