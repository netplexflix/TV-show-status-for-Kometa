<p align="center">
   <img width="567" height="204" alt="Image" src="https://github.com/user-attachments/assets/35eae37f-606c-4fbb-b063-fe80584e8af9" /><br>
   <a href="https://github.com/netplexflix/TV-show-status-for-Kometa/releases"><img alt="GitHub Release" src="https://img.shields.io/github/v/release/netplexflix/TV-show-status-for-Kometa?style=plastic"></a>
   <a href="https://hub.docker.com/repository/docker/netplexflix/tssk"><img alt="Docker Pulls" src="https://img.shields.io/docker/pulls/netplexflix/tssk?style=plastic"></a>
   <a href="https://discord.gg/VBNUJd7tx3"><img alt="Discord" src="https://img.shields.io/discord/1329439972796928041?style=plastic&label=Discord"></a>
</p>

TSSK (TV Show Status for Kometa) checks your [Sonarr](https://sonarr.tv/) for your TV Shows statuses and creates `.yml` files  
which can be used by [Kometa](https://kometa.wiki/) to create collections and overlays.

---

## Categories
- New shows, that were added in the past x days
- Shows with upcoming regular episodes within x days
- Shows for which a new season is airing within x days
- Shows for which a new season has been added which aired in the past x days
- Shows with upcoming season finales within x days
- Shows for which a season finale was added which aired in the past x days
- Shows for which a final episode was added which aired in the past x days
- Returning Shows
- Ended Shows
- Canceled Shows

<sub>Also see [UMTK](https://github.com/netplexflix/Upcoming-Movies-TV-Shows-for-Kometa) for adding a category for upcoming Movies and TV shows</sub>

---

## 📝 Table of Contents
- [🛠️ Installation](#installation)
  - [Option 1: Docker](#option-1-docker)
    - [Step 1: Install Docker](#step-1-install-docker)
    - [Step 2: Create docker-compose file](#step-2-create-docker-compose-file)
    - [Step 3: (Optional): Update volumes, Timezone and CRON Schedule](#step-3-optional-update-volumes-timezone-cron-schedule)
    - [Step 4: Create config](#step-4-create-config)
    - [Step 5: Configure your settings](#step-5-configure-your-settings)
    - [Step 6: Run TSSK](#step-6-run-tssk)
    - [Step 7: Add the yml files to your Kometa config](#step-7-add-yml-files-to-kometa-config)
  - [Option 2: Manual (Python)](#option-2-manual-python)
    - [Step 1: Download Script](#step-1-download-script)
    - [Step 2: Install dependencies](#step-2-install-dependencies)
    - [Step 3: Configure your settings](#step-3-configure-settings)
    - [Step 4: Run TSSK](#step-4-run-tssk)
    - [Step 5: Add the yml files to your Kometa config](#step-5-add-yml-files-to-kometa-config)
- [⚙️ Configuration](#configuration)
  - [General settings](#general-settings)
  - [Collection blocks](#collection-blocks)
  - [Overlay blocks](#overlay-blocks)
  - [Date formats](#date-formats)
- [☄️ Add the yml files to your Kometa config](#add-to-kometa-config)
- [🌐 Localization](#localization)
- [⚠️ Do you Need Help or have Feedback?](#help)

---

<a id="installation"></a>
## 🛠️ Installation


<a id="option-1-docker"></a>
### Option 1: Docker

<a id="step-1-install-docker"></a>
#### Step 1: Install Docker

1. **Download Docker Desktop** from [docker.com](https://www.docker.com/products/docker-desktop/)
2. **Install and start Docker Desktop** on your computer
3. **Verify installation**: Open a terminal/command prompt and type `docker --version` - you should see a version number

<a id="step-2-create-docker-compose-file"></a>
#### Step 2: Create Docker Compose File

1. **Create a new folder** for TSSK on your computer (e.g., `C:\TSSK` or `/home/user/TSSK`)
2. **Download the `docker-compose.yml`** and place it in that folder, or manually create it by copy pasting this content:

```yaml
version: "3.8"

services:
  tssk:
    image: netplexflix/tssk:latest
    container_name: tssk
    environment:
      - CRON=0 2 * * * # every day at 2am
      - DOCKER=true # important for path reference
      - TZ=Europe/Amsterdam # Set your timezone
    volumes:
      - ./config:/app/config
      - ./kometa:/config/kometa
    restart: unless-stopped
```

<a id="step-3-optional-update-volumes-timezone-cron-schedule"></a>
#### Step 3 (Optional): Update volumes, Timezone and CRON Schedule

By default the yml files will be output in a `kometa` subdirectory in your TSSK directory.
You can choose to have them output in a different location if you want.

> [!IMPORTANT]
> The format is: `your-actual-path:container-path`<br>
> Do **not** change the container-path parts

Example:
   - You want the output yml files to be output in your existing kometa config folder which is located at `/mnt/user/kometa/config`
   - Then your mount should look like this:
   ```
      - /mnt/user/kometa/config:/config/kometa
   ```

**Update the timezone** in the `TZ` environment variable to [match your location](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) (e.g.: `America/New_York`, `Europe/London`, `Asia/Tokyo`)<br>
**Update the CRON Schedule** if you want to schedule it differently from the default (daily at 2 AM). (Tip: [Crontab.Guru](https://crontab.guru/))

<a id="step-4-create-config"></a>
#### Step 4: Create a config

1. Create a subfolder named `config` 
2. Download `config/config.example.yml` and save it as `config.yml` in your config folder

<a id="step-5-configure-your-settings"></a>
#### Step 5: Configure Your Settings
- See [⚙️ Configuration](#️configuration)

<a id="step-6-run-tssk"></a>
#### Step 6: Run TSSK

1. **Open a terminal/command prompt** in your TSSK folder
2. **Type this command** and press Enter:
   ```bash
   docker-compose up -d
   ```
3. **That's it!** TSSK will now run automatically every day at 2 AM

<a id="step-7-add-yml-files-to-kometa-config"></a>
#### Step 7: Add the yml files to your Kometa config
- See [☄️ Add the yml files to your Kometa config](#️-add-to-kometa-config)

---

<a id="option-2-manual-python"></a>
### Option 2: Manual (Python)

<a id="step-1-download-script"></a>
#### Step 1: Download Script
```sh
git clone https://github.com/netplexflix/TV-show-status-for-Kometa.git
cd TV-show-status-for-Kometa
```

> [!TIP]
>If you don't know what that means, then simply download the script by pressing the green 'Code' button above and then 'Download Zip'.  
>Extract the files to your desired folder.

<a id="step-2-install-dependencies"></a>
#### Step 2: Install dependencies
- Ensure you have [Python](https://www.python.org/downloads/) installed (`>=3.11`).
- Open a Terminal in the script's directory
> [!TIP]
>Windows Users:  
>Go to the TSSK folder (where TSSK.py is). Right mouse click on an empty space in the folder and click `Open in Windows Terminal`.
- Install the required dependencies by running:
```sh
pip install -r requirements.txt
```
<a id="step-3-configure-settings"></a>
#### Step 3: Configure your settings
- See [⚙️ Configuration](#️configuration)

<a id="step-4-run-tssk"></a>
#### Step 4: Run TSSK
Open a Terminal in your script directory and launch the script with:
```sh
python TSSK.py
```

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

<a id="step-5-add-yml-files-to-kometa-config"></a>
#### Step 5: Add the yml files to your Kometa config
- See [☄️ Add the yml files to your Kometa config](#️-add-to-kometa-config)
  
---

<a id="configuration"></a>
## ⚙️ Configuration
Rename `config.example.yml` in your config folder to `config.yml` and edit the needed settings:

<a id="general-settings"></a>
### General settings:
- **sonarr_url:** Change if needed.
- **sonarr_api_key:** Can be found in Sonarr under settings => General => Security.
- **sonarr_timeout:** Increase if needed for large libraries.
- **use_tvdb:** Change to `true` if you prefer TheTVDB statuses for returning and ended. (note: TheTVDB does not have the 'canceled' status)
- **skip_unmonitored:** Default `true` will skip a show if the upcoming season/episode is unmonitored.
- **ignore_finales_tags:** Shows with these tags will be ignored when checking for finales.
>[!NOTE]
> For some shows, episodes are listed one at a time usually one week ahead in TheTVDB/Sonarr. Because of this, TSSK wrongly (yet logically..) thinks that the last episode listed in the season is a finale.
> You can give problematic shows like this a tag in Sonarr so TSSK will ignore finales for that show and treat the current 'last' episode of the season as a regular episode.

- **utc_offset:** Set the [UTC timezone](https://en.wikipedia.org/wiki/List_of_UTC_offsets) offset. e.g.: LA: -8, New York: -5, Amsterdam: +1, Tokyo: +9, etc

>[!NOTE]
> Some people may run their server on a different timezone (e.g. on a seedbox), therefor the script doesn't convert the air dates to your machine's local timezone. Instead, you can enter the utc offset you desire.<br>

- **simplify_next_week_dates:** Will simplify dates to `today`, `tomorrow`, `friday` etc if the air date is within the coming week.
- **process_:** Choose which categories you wish to process. Change to `false` to disable.

For each category, you can change the relevant settings:
- **future_days:** How many days into the future the script should look.
- **recent_days:** How many days in the past the script should look (for aired Finales)

<a id="collection-blocks"></a>
### Collection blocks:
- **collection block:**
  - **collection_name:** The name of the collection.
  - **smart_label:** Choose the sorting option. [More info here](https://metamanager.wiki/en/latest/files/builders/smart/#sort-options)
  - **sort_title:** Collection sort title.
  - etc

>[!TIP]
>You can enter any other Kometa variables in this block and they will be automatically added in the generated .yml files.</br>
>`collection_name` is used to name the collection and will be stripped from the collection block.

<a id="overlay-blocks"></a>
### Overlay blocks:  
- **backdrop block:**
  - **enable:** whether or not you want a backdrop (the colored banner behind the text)
  - Change backdrop size, color and positioning. You can add any relevant variables here. [More info here](https://kometa.wiki/en/latest/files/overlays/?h=overlay#backdrop-overlay)
    
- **text block:** 
  - **date_format:** The date format to be used on the overlays. e.g.: "yyyy-mm-dd", "mm/dd", "dd/mm", etc.
  - **capitalize_dates:** `true` will capitalize letters in dates.
  - **use_text:** Text to be used on the overlays before the date. e.h.: "NEW SEASON"
  - Change text color and positioning. You can add any relevant variables here. [More info here](https://kometa.wiki/en/latest/files/overlays/?h=overlay#text-overlay)
  - For `New Season Soon`, `New Season Started`, `Upcoming Finale` and `Season Finale` you can use [#] to display the season number

> [!TIP]
> `group` and `weight` are used to determine which overlays are applied in case multiple are valid.
> Example: You add a new show, for which season 2 just aired in full yesterday. In this case the following overlays would be valid: `new show`, `new season` and `season finale`.
> In the default config, `new show` has the highest weight (40) so that's the overlay that will be applied. If you prefer any of the other to be applied instead, you need to increase their weight.
> You can also choose to have multiple overlays applied at the same time by removing the group and weight, in case you put them in different positions.

<a id="date-formats"></a>
### Date formats:
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

<a id="add-to-kometa-config"></a>
## ☄️ Add the yml files to your Kometa config

Open your **Kometa** config.yml (typically at `Kometa/config/config.yml`, NOT your TSSK config file).  
Include paths to the generated .yml files under the relevant `TV Shows` library sections:

Manual install Example:

```yaml
TV Shows:
  metadata_files:
  - file: P:/Scripts/TSSK/kometa/TSSK_TV_NEW_SEASON_METADATA.yml
  overlay_files:
  - file: P:/scripts/TSSK/kometa/TSSK_TV_NEW_SEASON_OVERLAYS.yml
  - file: P:/scripts/TSSK/kometa/TSSK_TV_UPCOMING_EPISODE_OVERLAYS.yml
  - file: P:/scripts/TSSK/kometa/TSSK_TV_UPCOMING_FINALE_OVERLAYS.yml
  - file: P:/scripts/TSSK/kometa/TSSK_TV_CANCELED_OVERLAYS.yml
  - file: P:/scripts/TSSK/kometa/TSSK_TV_ENDED_OVERLAYS.yml
  - file: P:/scripts/TSSK/kometa/TSSK_TV_RETURNING_OVERLAYS.yml
  - file: P:/scripts/TSSK/kometa/TSSK_TV_SEASON_FINALE_OVERLAYS.yml
  - file: P:/scripts/TSSK/kometa/TSSK_TV_FINAL_EPISODE_OVERLAYS.yml
  - file: P:/scripts/TSSK/kometa/TSSK_TV_NEW_SEASON_STARTED_OVERLAYS.yml
  - file: P:/scripts/TSSK/kometa/TSSK_TV_NEW_SHOW_OVERLAYS.yml
  collection_files:
  - file: P:/scripts/TSSK/kometa/TSSK_TV_NEW_SHOW_COLLECTION.yml
  - file: P:/scripts/TSSK/kometa/TSSK_TV_NEW_SEASON_COLLECTION.yml
  - file: P:/scripts/TSSK/kometa/TSSK_TV_NEW_SEASON_STARTED_COLLECTION.yml
  - file: P:/scripts/TSSK/kometa/TSSK_TV_UPCOMING_EPISODE_COLLECTION.yml
  - file: P:/scripts/TSSK/kometa/TSSK_TV_UPCOMING_FINALE_COLLECTION.yml
  - file: P:/scripts/TSSK/kometa/TSSK_TV_SEASON_FINALE_COLLECTION.yml
  - file: P:/scripts/TSSK/kometa/TSSK_TV_FINAL_EPISODE_COLLECTION.yml
  - file: P:/scripts/TSSK/kometa/TSSK_TV_CANCELED_COLLECTION.yml
  - file: P:/scripts/TSSK/kometa/TSSK_TV_ENDED_COLLECTION.yml
  - file: P:/scripts/TSSK/kometa/TSSK_TV_RETURNING_COLLECTION.yml
```

> [!TIP]
> Only add the files for the categories you want to enable. All are optional and independently generated based on your config settings.
> If you add `TSSK_TV_NEW_SEASON_METADATA` the air date of the New Season premiere will be added to the beginning of the sort title so you can sort them by air date. 

---

<a id="localization"></a>
## 🌐 Localization

You can translate weekdays and months by using a localization file. <br>
- Download your language from this repo (`config/localization files`)
- Rename it to `localization.yml` and place it in your config folder (next to `config.yml`).

If your language is missing, simply use one of the templates and edit as needed.


---

<a id="help"></a>
### ⚠️ **Do you Need Help or have Feedback?**
- Join the [Discord](https://discord.gg/VBNUJd7tx3).
 
---  
### ❤️ Support the Project
If you like this project, please ⭐ star the repository and share it with the community!

<br/>

[!["Buy Me A Coffee"](https://github.com/user-attachments/assets/5c30b977-2d31-4266-830e-b8c993996ce7)](https://www.buymeacoffee.com/neekokeen)