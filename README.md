# 📺 TV Show Status for Kometa

This script checks your [Sonarr](https://sonarr.tv/) for your TV Shows statuses and creates .yml files which can be used by [Kometa](https://kometa.wiki/) to create collections and overlays.</br>


Categories:
*  New shows, that were added in the past x days
*  Shows with upcoming regular episodes within x days
*  Shows with upcoming season finales within x days
*  Shows for which a finale was added which aired in the past x days
*  Shows for which a new season is airing within x days
*  Shows for which a new season has been added which aired in the past x days
*  Returning Shows (new episodes or seasons are coming, but not within the timeframes chosen above)
*  Ended Shows (no new episodes or seasons are expected)

<sub>Also see [UTSK](https://github.com/netplexflix/Upcoming-TV-Shows-for-Kometa) for adding a category for upcoming TV shows</sub>

Example overlays (you can fully customize placement, colors, text, etc:
![Image](https://github.com/user-attachments/assets/e7c517cc-5164-41d9-8e5e-015577aad36e)

Example collection:</br>
<img width="696" height="403" alt="Image" src="https://github.com/user-attachments/assets/b52c411f-4d73-4386-93c4-38cee8ea2998" />

---

## ✨ Features
- 🗓️ **Detects upcoming episodes, finales and seasons**: Searches Sonarr for TV show schedules.
- 🏁 **Aired Finale labelling**: Use a separate overlay for shows for which a Finale was added.
-  ▼ **Filters out unmonitored**: Skips show if season/episode is unmonitored. (optional)
-  🪄 **Customizable**: Change date format, collection name, overlay positioning, text, ..
-  🌎 **Timezones**: Choose your timezone, regardless of where the script is ran from.
- ℹ️ **Informs**: Lists matched and skipped(unmonitored) TV shows.
- 📝 **Creates .yml**: Creates collection and overlay files which can be used with Kometa.

---

## 🛠️ Installation

### Choose your install method:

---

### ▶️ Option 1: Manual (Python)

1. Clone the repo:
```sh
git clone https://github.com/netplexflix/TV-show-status-for-Kometa.git
cd TV-show-status-for-Kometa
```

> [!TIP]
>If you don't know what that means, then simply download the script by pressing the green 'Code' button above and then 'Download Zip'.  
>Extract the files to your desired folder.

2. Install dependencies:
- Ensure you have [Python](https://www.python.org/downloads/) installed (`>=3.9`).
- Open a Terminal in the script's directory
> [!TIP]
>Windows Users:  
>Go to the TSSK folder (where TSSK.py is). Right mouse click on an empty space in the folder and click `Open in Windows Terminal`.
- Install the required dependencies by running:
```sh
pip install -r requirements.txt
```

---

### ▶️ Option 2: Docker

If you prefer not to install Python and dependencies manually, you can use the official Docker image instead.

1. Ensure you have [Docker](https://docs.docker.com/get-docker/) installed.
2. Download the provided `docker-compose.yml` from this repository (or copy the example below).
3. Run the container:
```sh
docker compose up -d
```

This will:
- Pull the latest `netplexfix/tssk` image from Docker Hub
- Run the script on a daily schedule (by default at 2AM)
- Mount your configuration and output directories into the container

You can customize the run schedule by modifying the `CRON` environment variable in `docker-compose.yml`.

> [!TIP]
> You can point the TSSK script to write overlays/collections directly into your Kometa folders by adjusting the volume mounts.

**Example `docker-compose.yml`:**

```yaml
version: "3.8"

services:
  tssk:
    image: netplexfix/tssk:latest
    container_name: tssk
    environment:
      - CRON=0 2 * * * # every day at 2am
      - DOCKER=true # important for path reference
    volumes:
      - /your/local/config/tssk:/app/config
      - /your/local/kometa/config:/config/kometa
    restart: unless-stopped
```

---

### 🧩 Continue Setup

### 1️⃣ Edit your Kometa config

Open your **Kometa** config.yml (typically at `Kometa/config/config.yml`, NOT your TSSK config file).  
Refer to the note above for where the files are saved depending on your setup.

The `.yml` files created by TSSK that Kometa uses are stored in different folders depending on how you're running the script:

- **Manual install**: files are saved directly to `kometa/` inside your TSSK folder (e.g. `TSSK/kometa/`)
- **Docker install**: files are saved to `/config/kometa/tssk/` inside the container — assuming you mount your Kometa config folder to `/config`

Make sure your Kometa config uses the correct path to reference those files.

In your Kometa config, include the following lines under your `TV Shows` library:

```yaml
TV Shows:
  overlay_files:
    - file: /config/tssk/TSSK_TV_NEW_SEASON_OVERLAYS.yml
    - file: /config/tssk/TSSK_TV_UPCOMING_EPISODE_OVERLAYS.yml
    - file: /config/tssk/TSSK_TV_UPCOMING_FINALE_OVERLAYS.yml
    - file: /config/tssk/TSSK_TV_SEASON_FINALE_OVERLAYS.yml
    - file: /config/tssk/TSSK_TV_FINAL_EPISODE_OVERLAYS.yml
    - file: /config/tssk/TSSK_TV_ENDED_OVERLAYS.yml
    - file: /config/tssk/TSSK_TV_RETURNING_OVERLAYS.yml
    - file: P:/TOOLS/Plex Meta Manager/config/TSSK/TSSK_TV_NEW_SEASON_STARTED_OVERLAYS.yml
    - file: P:/TOOLS/Plex Meta Manager/config/TSSK/TSSK_TV_NEW_SHOW_OVERLAYS.yml
  collection_files:
    - file: /config/tssk/TSSK_TV_NEW_SEASON_COLLECTION.yml
    - file: /config/tssk/TSSK_TV_UPCOMING_EPISODE_COLLECTION.yml
    - file: /config/tssk/TSSK_TV_UPCOMING_FINALE_COLLECTION.yml
    - file: /config/tssk/TSSK_TV_SEASON_FINALE_COLLECTION.yml
    - file: /config/tssk/TSSK_TV_FINAL_EPISODE_COLLECTION.yml
    - file: /config/tssk/TSSK_TV_ENDED_COLLECTION.yml
    - file: /config/tssk/TSSK_TV_RETURNING_COLLECTION.yml
```

> [!TIP]
> Only add the files for the categories you want to enable. All are optional and independently generated based on your config settings.

### 2️⃣ Edit your configuration file
---

## ⚙️ Configuration
Rename `config.example.yml` to `config.yml` and edit the needed settings:

- **sonarr_url:** Change if needed.
- **sonarr_api_key:** Can be found in Sonarr under settings => General => Security.
- **skip_unmonitored:** Default `true` will skip a show if the upcoming season/episode is unmonitored.
- **utc_offset:** Set the [UTC timezone](https://en.wikipedia.org/wiki/List_of_UTC_offsets) offset. e.g.: LA: -8, New York: -5, Amsterdam: +1, Tokyo: +9, etc

>[!NOTE]
> Some people may run their server on a different timezone (e.g. on a seedbox), therefor the script doesn't convert the air dates to your machine's local timezone. Instead, you can enter the utc offset you desire.

</br>

For each category, you can change the relevant settings:
- **future_days:** How many days into the future the script should look.
- **recent_days:** How many days in the past the script should look (for aired Finales)

- **collection block:**
  - **collection_name:** The name of the collection.
  - **smart_label:** Choose the sorting option. [More info here](https://metamanager.wiki/en/latest/files/builders/smart/#sort-options)
  - **sort_title:** Collection sort title.
  - etc
>[!TIP]
>You can enter any other Kometa variables in this block and they will be automatically added in the generated .yml files.</br>
>`collection_name` is used to name the collection and will be stripped from the collection block.
  
- **backdrop block:**
  - **enable:** whether or not you want a backdrop (the colored banner behind the text)
  - Change backdrop size, color and positioning. You can add any relevant variables here. [More info here](https://kometa.wiki/en/latest/files/overlays/?h=overlay#backdrop-overlay)
    
- **text block:** 
  - **date_format:** The date format to be used on the overlays. e.g.: "yyyy-mm-dd", "mm/dd", "dd/mm", etc.
  - **capitalize_dates:** `true` will capitalize letters in dates.
  - **use_text:** Text to be used on the overlays before the date. e.h.: "NEW SEASON"
  - Change text color and positioning. You can add any relevant variables here. [More info here](https://kometa.wiki/en/latest/files/overlays/?h=overlay#text-overlay)


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

If you're using the **Docker setup**, the script will run automatically according to the schedule defined by the `CRON` variable in your `docker-compose.yml`.  
You can inspect the container logs to see output and monitor activity:

```sh
docker logs -f tssk
```

If you're using the **manual install**, follow the instructions below to run the script manually.

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
>"C:\Users\User1\AppData\Local\Programs\Python\Python311\python.exe" "P:\TSSK\TSSK.py" -r
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
