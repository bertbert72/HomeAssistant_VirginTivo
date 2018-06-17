# HomeAssistant_VirginTivo
HomeAssistant component for control of Virgin Media Tivo boxes

Features are

+ Supports multiple boxes
+ Configurable list of channels
+ Shows current channel
+ Set channel through dropdown
+ Can restrict channels shown in dropdown
+ Automatically switch to HD version of channel

Sample configuration in repository with full list of Virgin Media channels.

Platform settings are:

Name | Description | Example
------------ | ------------- | -------------
platform | Must be virgintivo | virgintivo
showbydefault | Whether all channels default to shown/hidden | true
hdverbydefault | Whether to switch to HD if available | false

The Tivos should be listed under the `tivos:` section.  Each entry has two required settings.

Name | Description | Example
------------ | ------------- | -------------
name | Friendy name of Tivo box | Virgin Tivo
host | IP or name of Tivo box | TIVO-C68000012345678

Channels come under the `channels:` section.  Each entry has a number of optional settings and one required setting (name).

Name | Description | Example
------------ | ------------- | -------------
name | Friendy name of channel | BBC One
hdver | Channel number of HD version if applicable | 108
show | Whether or not to show the channel in the sources list | false
plusone | Not implemented yet | -

Here's an example:
```
  - platform: virgintivo
    showbydefault: false
    hdverbydefault: true
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
        hdver: 108
        show: true
      102:
        name: BBC Two
        hdver: 162
        show: true
      103:
        name: ITV
        hdver: 113
        show: true
      104:
        name: Channel 4
        hdver: 141
        show: true
      105:
        name: Channel 5
        hdver: 150
        show: true
```
