# Home Assistant VirginTivo
Home Assistant component for control of Virgin Media Tivo boxes

![Virgin Tivo component for Home Assistant](img/HA-VT01.png "Virgin Tivo component for Home Assistant")
![Source list](img/HA-VT02.png "Source List")

Features are

+ Supports multiple boxes
+ Configurable list of channels (see /resources for a tool to help)
+ Optionally update list of channels automatically from TV Channel Lists
+ Automatically switch to HD version of channel
+ Show current channel
+ Set channel through dropdown
+ Can restrict channels shown in dropdown
+ Switch between +1 and normal version of channel
+ Depending on whether the channel is available on Virgin Go
  + Display programme information
  + Display grab of current programme
+ Optionally use Tivo remote to control other media player devices (obscure I know!)
+ Services: find remote, send IR code, send keyboard command, last channel, live TV, switch to/from +1 channel, search for programme, subtitles on/off, "teleport".

A sample configuration is in the repository with a full list of Virgin Media channels.  Note that a channel scraper has been added in /resources to get the latest channels in a compatible format from https://www.tvchannellists.com.  

Alexa automation hints are provided in the automations/alexa folder by garywilson4.

# Usage
+ Drop the file into the custom_components/media_player directory.
+ Edit your configuration file to add the `virgintivo` platform to the `media_player:` section.

# Configuration
There are is one required section: tivos, two sections of which at least one is required: tvchannellists and channels, plus one optional section: guide.

Platform settings are:

| Name | Default | Description | Example |
|:---- |:-------:|:------------|:--------|
| platform _(req)_ | | Must be virgintivo | virgintivo |
| default_is_show _(opt)_ | true | Channels default to shown/hidden | true |
| force_hd _(opt)_ | false | Switch to HD if available | false |
| keep_connected _(opt)_ | false | Persistent telnet connection to Tivo | false |
| show_packages _(opt)_ |  | TV packages to show | Free-to-air,Player,Mix,Fun,Full House |

**NB:** if using the _force_hd_ functionality, it is advisable to set _scan_interval_ to a low value, e.g. 1 to allow the component to change to the HD channel quickly.

## tivos
The Tivos should be listed under the `tivos:` section.  Each entry has two required settings and one optional.

| Name | Default | Description | Example |
|:-----|:--------|:------------|:--------|
| name _(req)_ | | Friendy name of Tivo box | Virgin Tivo |
| host _(req)_ | | IP or name of Tivo box | TIVO-C68000012345678 |
| force_hd _(opt)_ | false | Switch to HD if available | false |
| keep_connected _(opt)_ | false | Persistent telnet connection to Tivo | false |

## tvchannellists
This allows automatic updating of the channel lists from the TV Channel Lists site. Overrides are available to customise the list as required.

NB: If both _tvchannellists_ and _channels_ are configured, the site will be tried first and if this fails the local channel configuration will be used.

| Name | Default | Description | Example |
|:-----|:--------|:------------|:--------|
| enable _(req)_ | | Enable this functionality | True |
| url _(opt)_<sup>1</sup> | | URL for channel listing | |
| ignore_channels _(opt)_ | | Ignore these channels from the site | 0 |
| show_channels _(opt)_ | | Show the channel in the sources list | 101,102,103,104 |
| hide_channels _(opt)_ | | Hide the channel in the sources list | 990,991,992,993 |
| logos _(opt)_ | | Channel logo to display | <pre>101: https://www.mysite.uk/images/bbcone.png</pre> |
| targets _(opt)_ | | HA entity to change | <pre>901: media_player.family_room</pre> |
| sources _(opt)_ | | Source on _target_ to choose | <pre>901: Virgin V6</pre> |
| override _(opt)_ | | Override for a channel | <pre>override:<br>  101:<br>    name: BBC One<br>    package: Player<br>    is_hd: False</pre> |

<sup>1</sup> The built-in URL used is currently https://www.tvchannellists.com/List_of_channels_on_Virgin_Media_(UK).  It is not recommended to change this as the component is unlikely to understand a different site.

## channels
Channels come under the `channels:` section.  Each entry has a number of optional settings and one required setting (name).  Use next/previous track to switch between the +1 and normal versions of a channel.

| Name | Default | Description | Example |
|:-----|:--------|:------------|:--------|
| name _(req)_ | | Friendy name of channel | BBC One |
| show _(opt)_ | | Show the channel in the sources list | false |
| package _(opt)_ | | TV package | Mix |
| hd_channel _(opt)_ | | HD channel number if applicable | 108 |
| plus_one _(opt)_ | | +1 channel number if applicable | 114 |
| logo _(opt)_ | | Channel logo to display | http://freeview.com/images/e4.png |
| target _(opt)_ | | HA entity to change | media_player.main_tv |
| source _(opt)_ | | Source on _target_ to choose | HDMI2 |

## guide
The guide settings come under the `guide:` section.  This section has a number of optional settings.

| Name | Default | Description | Example |
|:-----|:--------|:------------|:--------|
| enable_guide _(opt)_ | true | Enable the guide functionality | false |
| cache_hours _(opt)_ | 12 | How many hours of the guide to preload | 12 |
| picture_refresh _(opt)_ | 60 | Seconds between screen updates | 60 |

# Services

These can be called by automations, scripts etc.

| Service | Entity | Description | Example Data |
| :------ | :----- | :---------- | :----------- |
| Find Remote <sup>1</sup> | media_player.virgintivo_find_remote | Causes the remote to beep | {"entity_id": "media_player.virgin_v6"} |
| Send IR Code | media_player.virgintivo_ircode | Sends an IR command | {"entity_id": "media_player.virgin_v6", "command": "standby"}<br>{"entity_id": "media_player.virgin_v6", "command": "advance", "repeats": 10}|
| Send Keyboard Command | media_player.virgintivo_keyboard | Sends a key entry | {"entity_id": "media_player.virgin_v6", "command": "A"} | Last Channel | media_player.virgintivo_last_channel | Return to previous channel | {"entity_id": "media_player.virgin_v6"} |
| Live TV | media_player.virgintivo_live_tv | Switch to normal TV mode | {"entity_id": "media_player.virgin_v6"} |
| Plus One Off | media_player.virgintivo_plus_one_off | Switch to non +1 version of channel | {"entity_id": "media_player.virgin_v6"} |
| Plus One On | media_player.virgintivo_plus_one_on | Switch to +1 version if available | {"entity_id": "media_player.virgin_v6"} |
| Search | media_player.virgintivo_search | Search for a programme | {"entity_id": "media_player.virgin_v6", "command": "family guy"} |
| Subtitles Off | media_player.virgintivo_subtitles_off | Turn off subtitles | {"entity_id": "media_player.virgin_v6"} |
| Subtitles On | media_player.virgintivo_subtitles_on | Turn on subtitles | {"entity_id": "media_player.virgin_v6"} |
| Teleport <sup>2</sup> | media_player.virgintivo_teleport | Change mode | {"entity_id": "media_player.virgin_v6", "command": "livetv"} |

<sup>1</sup> Works with the Virgin V6 Bluetooth remote

<sup>2</sup> This forces the Tivo into certain modes.  Known available entries are: TIVO, LIVETV, GUIDE, NOWPLAYING

# Example

This is a truncated example only.  Use example.yaml in the repository for a full set of channels and /resources for a tool to create this configuration.

```
  - platform: virgintivo
    default_is_show: false
    force_hd: true
    tivos:
      1:
        name: Virgin V6
        host: TIVO-C68000012345678
      2:
        name: Virgin Tivo
        host: TIVO-CF0000012345678
    channels:
      100:
        name: Virgin Media Previews
      101:
        name: BBC One
        hd_channel: 108
        show: true
      102:
        name: BBC Two
        hd_channel: 162
        show: true
      103:
        name: ITV
        hd_channel: 113
        show: true
        plus_one: 114
      104:
        name: Channel 4
        hd_channel: 141
        plus_one: 142
      105:
        name: Channel 5
        hd_channel: 150
        plus_one: 155
```
