![Screenshot](https://raw.githubusercontent.com/bertbert72/HomeAssistant_VirginTivo/master/img/HA-VT03.png "Screenshot")

##  Features

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
+ Supports automated component updating via _HACS_ and _custom_updater_

## Configuration

This is a minimal example only and uses the online channel list.  Refer to the examples in the repository for other ways of setting up the component.

```
  - platform: virgintivo
    tivos:
      1:
        name: Virgin V6
        host: TIVO-C68000020000000
    tvchannellists:
      enable: True
```
