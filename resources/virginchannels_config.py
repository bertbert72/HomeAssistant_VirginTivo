# The URL for the TV channels page
vc_url = "https://www.tvchannellists.com/List_of_channels_on_Virgin_Media_(UK)"
# Configuration filename
config_filename = "virgintivo.yaml"

# Channels to ignore
ignore_ids = ["0"]
# Channels to be shown in drop down (when default_is_show = False)
show_channels = ["101", "102", "103", "104", "105", "106", "110", "115", "117", "118", "121", "124", "126", "127",
                 "132", "135", "139", "147", "428", "875", "876"]
# Channels to be shown in drop down (when default_is_show = True)
hide_channels = ["990", "992", "993", "994", "995", "996"]
# Channel logos
logos = {"875": "https://www.freeview.co.uk/app/themes/freeview/assets/images/channels/entertainment/rteone.png",
         "876": "https://www.freeview.co.uk/app/themes/freeview/assets/images/channels/entertainment/rteone.png"}
# Targets
targets = {"901": "media_player.family_room",
           "902": "media_player.family_room",
           "903": "media_player.family_room"}
# Sources
sources = {"901": "Virgin V6",
           "902": "Virgin Tivo",
           "903": "CCTV"}
# Channel overrides
override = {"101": ["BBC One", "Player", False],
            "108": ["BBC One HD", "Player", True],
            "159": ["Liverpool TV", "Player", False],
            "251": ["Discovery Channel HD", "Full House", True]}

# Top of config file
top_of_config = """  - platform: virgintivo
    default_is_show: false
    default_is_hd: true
    scan_interval: 1
    show_packages: Mix,Premium
    tivos:
      1:
        name: Virgin V6
        host: TIVO-C68000000000000
        force_hd: true
      2:
        name: Virgin Tivo
        host: TIVO-CF0000000000000
        force_hd: true
    guide:
      picture_refresh: 60"""