# Channel List Scraper
Allows automatic creation of a YAML configuration file containing the latest channels from https://www.tvchannellists.com

## Setup
+ Download the files into a folder
+ Install the requirements if needed, e.g. `pip3 install -r requirements.txt`.
+ Edit the `virginchannels_configuration.py` file as required

## Usage
+ Run the script using `python3 virginchannels.py`
+ Use the output `virgintivo.yaml` directly or incorporate into your `configuration.yaml`

## Configuration Variables
| Name | Description | Example |
|:---- |:------------|:--------|
| vc_url | URL for channel site | "https://www.tvchannellists.com/List_of_channels_on_Virgin_Media_(UK)" |
| config_filename | Output file | "virgintivo.yaml" |
| ignore_ids | Channels to supress | ["0"] |
| show_channels | Channels to always show in drop down | ["101", "102", "103"] |
| hide_channels | Channels to always hide in drop down | ["990", "992"] |
| logos | Channel logos | ["101": "http://mysite.com/logos/BBCOne.png"] |
| targets | Values for the target option | {"901": "media_player.family_room"} |
| sources | Values for the source option | {"901": "Virgin V6"} |
| override | Custom overrides, e.g. for BBC One HD | {"108": ["BBC One HD", "Player", True]} |
| top_of_config | The config before channels... | """  - platform: virgintivo |
