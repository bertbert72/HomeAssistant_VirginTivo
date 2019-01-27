import requests
from bs4 import BeautifulSoup

from virginchannels_config import *


class Channel:
    def __init__(self, channel_id, channel_name, package, is_hd):
        self.channel_id = channel_id
        self.channel_name = channel_name
        self.package = package
        self.is_hd = is_hd
        self.is_plus_one = False
        self.base_name = ""
        self.show = ""
        self.hd_ver = ""
        self.plus_one_ver = ""
        self.logo = ""
        self.target = ""
        self.source = ""


def contains(this_cell, this_string):
    if this_string in this_cell:
        return True
    else:
        return False


def base_name(channel_name):
    return str(channel_name).replace(" +1", "").replace(" ja vu", "").replace(" HD", "")


res = requests.get(vc_url)
soup = BeautifulSoup(res.text, "html.parser")

all_channels = {}

for channel_id, channel_details in override.items():
    if channel_id not in ignore_ids:
        channel_name = channel_details[0].strip()
        channel_name = "'{}'".format(channel_name) if "&" in channel_name else channel_name
        package = channel_details[1].strip()
        is_hd = channel_details[2]
        ignore_ids.append(channel_id)
        all_channels[channel_id] = Channel(channel_id, channel_name, package, is_hd)
        if "+1" in channel_name or "ja vu" in channel_name:
            all_channels[channel_id].is_plus_one = True
        if base_name(channel_name) != channel_name:
            all_channels[channel_id].base_name = base_name(channel_name)

for table in soup.find_all(class_=["wikitable sortable"]):
    for row in table.findAll("tr"):
        cells = row.findAll(["td"])
        if len(cells) >= 6:
            if cells[1].find(text=True).strip() == "Local TV":
                cells[5] = BeautifulSoup("Player", "html.parser")
                cells[6] = BeautifulSoup("SDTV", "html.parser")
            if cells[6].find(text=True) is not None:
                channel_id = cells[0].find(text=True).strip()
                if channel_id not in ignore_ids:
                    channel_name = cells[1].find(text=True).split('/')[0].strip()
                    channel_name = "'{}'".format(channel_name) if "&" in channel_name else channel_name
                    package = cells[5].find(text=True).strip()
                    is_hd = contains(cells[6].find(text=True), "HDTV")
                    ignore_ids.append(channel_id)
                    all_channels[channel_id] = Channel(channel_id, channel_name, package, is_hd)
                    if "+1" in channel_name or "ja vu" in channel_name:
                        all_channels[channel_id].is_plus_one = True
                    all_channels[channel_id].base_name = base_name(channel_name)

for channel in all_channels.values():
    if not channel.is_hd and not channel.is_plus_one:
        hd_id = next((hd_id for hd_id, hd_ch in all_channels.items()
                      if hd_ch.base_name == channel.base_name and hd_ch.is_hd), None)
        if hd_id is not None:
            channel.hd_ver = hd_id
    if not channel.is_plus_one:
        plus_one_id = next((plus_one_id for plus_one_id, plus_one_ch in all_channels.items()
                            if plus_one_ch.base_name == channel.base_name and plus_one_ch.is_plus_one), None)
        if plus_one_id is not None:
            channel.plus_one_ver = plus_one_id

for channel_id in show_channels:
    if channel_id in all_channels:
        all_channels[channel_id].show = "true"

for channel_id in hide_channels:
    if channel_id in all_channels:
        all_channels[channel_id].show = "false"

for channel_id, logo_url in logos.items():
    if channel_id in all_channels:
        all_channels[channel_id].logo = logo_url

for channel_id, source_name in sources.items():
    if channel_id in all_channels:
        all_channels[channel_id].source = source_name

for channel_id, target_name in targets.items():
    if channel_id in all_channels:
        all_channels[channel_id].target = target_name

entry = "    channels:\n"
for channel_id, channel in sorted(all_channels.items()):
    entry += "      {}:\n".format(channel.channel_id)
    entry += "        name: {}\n".format(channel.channel_name)
    entry += "        show: {}\n".format(channel.show) if channel.show != "" else ""
    entry += "        package: {}\n".format(channel.package)
    entry += "        hd_channel: {}\n".format(channel.hd_ver) if channel.hd_ver != "" else ""
    entry += "        plus_one: {}\n".format(channel.plus_one_ver) if channel.plus_one_ver != "" else ""
    entry += "        logo: {}\n".format(channel.logo) if channel.logo != "" else ""
    entry += "        target: {}\n".format(channel.target) if channel.target != "" else ""
    entry += "        source: {}\n".format(channel.source) if channel.source != "" else ""

with open(config_filename, 'w') as f:
    print(top_of_config, file=f)
    print(entry, file=f)
